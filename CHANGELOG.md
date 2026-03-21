# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に従っています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-21
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを実装。パッケージバージョンは `0.1.0`。
  - パブリック API のエクスポート: data, strategy, execution, monitoring（__all__ を定義）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルート判定は __file__ を基点に `.git` または `pyproject.toml` を探索して行うため、CWD に依存しない。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサは以下に対応:
    - コメント行（#）や `export KEY=val` 形式の扱い。
    - シングル/ダブルクォート内のエスケープ処理。
    - クォート無しの行でのインラインコメントの取り扱い（直前が空白/タブの場合はコメントと判断）。
  - 上書き制御:
    - `.env` 読み込みは既存 OS 環境を保護（protected set）。
    - `.env.local` は override=True で OS 環境を上書き可能（ただし protected は上書きしない）。
  - Settings クラスを提供（環境変数から typed プロパティを取得）:
    - J-Quants / kabuステーション / Slack / DB パス / ログレベル / 環境（development/paper_trading/live）等。
    - 必須値未設定時は明確なエラーを投げる。

- Data 層（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - 自動リトライ（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）。
    - 401 受信時はリフレッシュトークンを利用して自動で id_token を更新し 1 回リトライ。
    - ページネーション対応で複数ページを連続取得（pagination_key を利用）。
    - 取得時刻（fetched_at）は UTC ISO 8601 形式で記録し、Look-ahead バイアスのトレースを可能に。
  - データ取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
  - DuckDB 保存関数（冪等）:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - PK 欠損行はスキップし、スキップ数をログ出力。
  - 型安全かつ堅牢な変換ユーティリティを実装:
    - _to_float / _to_int（不正値や空値は None を返す。小数を含む文字列からの int 変換は慎重に扱う）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集ロジックを実装。
    - デフォルト RSS ソースを定義（例: Yahoo Finance ビジネスカテゴリ）。
    - 記事 ID は URL 正規化後の SHA-256（先頭 32 文字）を用いて冪等性を担保。
    - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ（utm_* 等）の除去、フラグメント除去、クエリパラメータのソート。
    - テキスト前処理（URL 除去・空白正規化）や受信サイズ上限（10MB）によるメモリ DoS 防止。
    - XML パースに defusedxml を利用して XML Bomb 等の攻撃を軽減。
    - HTTP(S) スキーム以外の URL を拒否することで SSRF を抑止する方針（実装方針として明記）。
    - バルク INSERT をチャンク化（デフォルト 1000 件）して SQL/パラメータ上限に配慮。
    - DB 保存は 1 トランザクションにまとめて実行。実際に挿入されたレコード数を正確に返す設計。

- リサーチ / ファクター（kabusys.research）
  - factor_research モジュール:
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR・相対 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER・ROE）を DuckDB の prices_daily / raw_financials を参照して計算。
    - ウィンドウ不足時は None を返す設計（堅牢な欠損処理）。
    - 各関数は (date, code) キーの辞書リストを返す。
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns）: 1/5/21 営業日等のホライズンで将来リターンを一括取得する効率的な SQL 実装。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装。サンプル不足（<3）や分散 0 の場合は None を返す。
    - rank, factor_summary 等のユーティリティ: 平均/標準偏差/中央値等の統計サマリーを提供。
  - research パッケージの __all__ に主要関数をエクスポート。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究環境で計算した raw ファクターを読み込み、正規化・合成して features テーブルへ保存する処理を実装。
    - フロー: research の calc_momentum/calc_volatility/calc_value を呼び出し、ユニバースフィルタを適用 → Z スコア正規化 → ±3 でクリップ → features に日付単位で置換（冪等）。
    - ユニバース基準: 最低株価 300 円、20 日平均売買代金 5 億円。
    - 正規化対象カラムを限定し、Z スコア処理は kabusys.data.stats.zscore_normalize を利用。
    - DB 書き込みはトランザクション + バルク挿入で原子性を保証。エラー時はロールバックを試行。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ保存する。
    - 各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算するユーティリティ実装。
      - momentum: 複数モメンタム要素のシグモイド平均。
      - value: PER に基づく逆数スコア（PER=20 -> 0.5 を基準）。
      - volatility: atr_pct の逆転シグモイド。
      - liquidity: 出来高比のシグモイド。
    - AI ニューススコアは存在すればシグモイドで変換、未登録は中立で補完。
    - weights の取り扱い:
      - デフォルト重みを定義（momentum 0.40 等）。
      - ユーザ指定の weights は検証して不正値を除外。合計が 1.0 でない場合は正規化。
    - Bear レジーム判定: ai_scores の regime_score 平均が負でかつサンプル数閾値を満たす場合は Bear と判定し BUY を抑制。
    - SELL（エグジット）条件（実装）:
      - ストップロス: 終値/avg_price - 1 < -8%（最優先）。
      - スコア低下: final_score が threshold 未満。
      - （未実装だが設計に含まれる）トレーリングストップや時間決済は将来的な拡張対象としてコメントあり。
    - signals テーブルへの書き込みは日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。
    - 生成結果は BUY/SELL の合計件数を返す。

- パッケージ API
  - strategy パッケージは build_features と generate_signals を公開（__all__）。

### Security
- news_collector で defusedxml を使用して XML パースの安全性を向上。
- ニュース URL 正規化時にトラッキングパラメータを削除し、SSRF やトラッキング情報の混入リスクを軽減する方針を実装。
- J-Quants クライアントはタイムアウト・リトライ・トークン更新等を実装し、堅牢な HTTP 通信を目指す。

### Notes / Implementation details
- DuckDB を前提に SQL を組み、可能な限り SQL 内で集約・ウィンドウ関数を使うことでデータスキャンを最小化する設計。
- 欠損・非数値・データ不足に対する防御（None の扱い、math.isfinite チェック、サンプル閾値など）を随所に入れている。
- ロギング（logger）を用いて警告・情報を出力し、運用時のトラブルシューティングを支援する。

---

今後の予定（例）
- execution 層（kabuステーション連携）の実装・テスト。
- トレーリングストップや時間決済などの追加エグジット条件の実装。
- news_collector のソース追加・記事→銘柄紐付け（news_symbols）ロジックの実装強化。
- 単体テスト・統合テストの追加と CI の整備。

（この CHANGELOG はコードベースの内容から推測して作成しています。リリースノートと差異がある場合は適宜更新してください。）