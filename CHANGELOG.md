# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
この CHANGELOG は "Keep a Changelog" の形式に準拠します。

なお、本ファイルはコードベースの内容から推測して作成しています。実際のコミット履歴とは差異がある場合があります。

## [Unreleased]

- 現時点で未リリースの変更点はありません。

## [0.1.0] - 2026-03-20

初回公開リリース。

### 追加 (Added)

- パッケージ基盤
  - kabusys パッケージを導入。バージョンは 0.1.0。
  - パッケージ公開用の __all__ と __version__ を定義。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを実装。
  - 自動 .env 読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサーは以下をサポート:
    - 空行 / コメント行の無視、`export KEY=val` 形式の対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート外のインラインコメント判定（直前が空白/タブの場合のみ）
  - 必須キー未設定時に ValueError を送出する _require() を提供。
  - KABUSYS_ENV / LOG_LEVEL の検証（受け入れ可能な値セットを定義）。
  - データベースパス（DUCKDB_PATH / SQLITE_PATH）を Path 型で取得。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - レート制限 (120 req/min) を固定間隔スロットリングで守る RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大再試行回数、408/429/5xx の扱い）を実装。
  - 401 受信時の自動トークンリフレッシュ（1 回）を実装、id_token のキャッシュ共有。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。挿入は ON CONFLICT DO UPDATE などで重複を排除。
  - 数値変換ユーティリティ (_to_float / _to_int) を実装（不正値を None に正しく扱う）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得して raw_news に保存するニュース収集モジュールを実装。
  - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を保証。
  - URL 正規化でトラッキングパラメータ除去、クエリソート、フラグメント削除などを実装。
  - defusedxml を使用して XML Bomb 等の攻撃を防止。
  - 受信バイト数上限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策、HTTP スキーム検証等の安全対策を実施。
  - バルク INSERT のチャンク処理などパフォーマンス考慮。

- 研究用ファクター計算・解析 (src/kabusys/research/*.py)
  - factor_research モジュールにてモメンタム / ボラティリティ / バリュー等のファクター計算関数を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA の要件含む）
    - calc_volatility: ATR20, atr_pct, avg_turnover, volume_ratio（true range の NULL 伝播制御）
    - calc_value: per, roe（raw_financials の最新レコード参照）
  - feature_exploration モジュールにて研究支援ユーティリティを実装:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターン算出
    - calc_ic: Spearman のランク相関（IC）計算。サンプル不足時の None 戻し。
    - rank: 同順位の平均ランク処理（丸めによる tie 対策）
    - factor_summary: count/mean/std/min/max/median を返す統計サマリ機能
  - research パッケージの公開 API を整理。

- 戦略層 (src/kabusys/strategy/*.py)
  - feature_engineering.build_features:
    - research モジュールが提供する生ファクターを取得し、ユニバースフィルタ（最低株価 / 平均売買代金）を適用。
    - 正規化（zscore_normalize を利用）・±3 でのクリップを行い features テーブルへ日付単位で置換（トランザクションで原子性確保）。
    - ユニバース判定に当日の欠損を補うため target_date 以前の最新価格を参照。
  - signal_generator.generate_signals:
    - features と ai_scores を組み合わせ、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを計算。
    - シグモイド変換や欠損コンポーネントの中立補完（0.5）を行い重み付き合算で final_score を算出。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY を抑制。
    - BUY 閾値（デフォルト 0.60）、STOP-LOSS（-8%）等ルールに基づき BUY/SELL シグナルを生成。
    - positions / prices を参照してエグジット判定を行い、signals テーブルへ日付単位で置換保存（原子性確保）。
    - 重みの入力をバリデーションし、既定値とマージ・合計が 1.0 でなければ再スケール。

- データ処理共通ユーティリティ
  - zscore_normalize を用いた正規化フローを研究層と戦略層で共有（kabusys.data.stats 経由でエクスポート）。

### 変更 (Changed)

- 設計上の方針を明文化:
  - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用する設計を徹底。
  - 発注 / execution 層への直接依存を持たない、戦略は signals テーブルを書き出すのみの設計。
  - DuckDB への書き込みはトランザクションとバルク操作で原子性・効率性を確保。

### 修正 (Fixed)

- データ整合性・耐障害性の改善:
  - J-Quants クライアントの JSON デコードエラー時に詳細メッセージを出すように修正。
  - save_* 系で PK 欠損レコードをスキップし、スキップ数を警告ログで通知。
  - _to_int/_to_float での変換失敗を安全に None に変換することで不正な値による破壊的更新を回避。
  - DuckDB 操作時に例外発生した場合の ROLLBACK を試み、失敗時はログで警告するように実装（generate_signals, build_features）。

### セキュリティ (Security)

- ニュース取得で defusedxml を利用し XML 関連攻撃を防止。
- RSS 処理で受信バイト数上限や HTTP スキーム検証を実装し、メモリ DoS / SSRF のリスク低減を図る。
- API リクエストでトークン管理・自動更新を実装し、不正な資格情報状態での無限ループを防止（allow_refresh フラグの設計）。

### ドキュメント・ロギング (Documentation / Logging)

- 各モジュールに docstring を充実させ、処理フロー・設計方針・期待する入出力を明記。
- 主要処理に logger による info/debug/warning を追加し運用時のトラブルシューティングに配慮。

---

今後の予定（例、TODO）
- positions テーブルに peak_price / entry_date 等を追加してトレーリングストップや時間決済を実装。
- AI スコアの生成パイプライン（news → ai_scores）およびその学習基盤の導入。
- モニタリング・アラート (Slack 連携) と実運用用 execution 層の統合。