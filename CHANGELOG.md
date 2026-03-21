# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
リリース日はこのドキュメント生成日時です。

## [0.1.0] - 2026-03-21

初回リリース。

### 追加 (Added)

- コアパッケージ
  - パッケージ初期化を追加（kabusys.__init__）。バージョンは 0.1.0。
  - 公開モジュール群: data, strategy, execution, monitoring をパッケージ API として公開。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索し、パッケージ配布後も CWD に依存しない自動ロードを実現。
  - 自動ロード順序: OS 環境変数 > .env.local > .env（.env.local は override=true）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト向け）。
  - 高度な .env パーサを実装: export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ、コメント処理などを正しく扱う。
  - 必須キー検査用ヘルパー _require を提供（未設定時は ValueError を送出）。
  - 環境値バリデーション: KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証とユーティリティプロパティ（is_live / is_paper / is_dev）。

- データ取得・永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限 (120 req/min) を守る固定間隔スロットリング RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx をリトライ対象に含む。
  - 401 Unauthorized を受けた場合のトークン自動リフレッシュ（1 回のみ）を実装。トークン取得用 API (get_id_token) を提供。
  - ページネーション対応の fetch_* 関数を提供:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）を実装:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアスのトレースを可能に。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集モジュールを実装。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリキーソート）を実装し、記事IDを安定ハッシュで生成（重複防止）。
  - セキュリティ対策: defusedxml を使用して XML Bomb 等を防止、HTTP/HTTPS 以外のスキーム拒否、受信サイズ上限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策、SSRF/ホスト解決に対する基本検査を導入。
  - バルク INSERT のチャンク処理・トランザクションで DB 負荷を抑制し、INSERT RETURNING 等で実挿入数を取得する設計（実装上の方針を明記）。

- リサーチ（ファクター計算） (kabusys.research)
  - factor_research モジュールを実装:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を制御して正確にカウント。
    - calc_value: raw_financials と prices_daily を組み合わせて per / roe を計算。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）での将来リターンを算出（単一クエリで取得、スキャン範囲にバッファを使用）。
    - calc_ic: Spearman のランク相関（Information Coefficient）計算。データ不足（<3）時は None を返す。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - rank: 同順位は平均ランクを与えるランク変換ユーティリティ（丸めで ties 検出の頑健性を確保）。
  - 研究用モジュールは外部ライブラリ（pandas 等）に依存せず、DuckDB のみを使用する設計。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research モジュールで作成した raw ファクターを集約・正規化して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8 円）を実装。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でのクリップを適用して外れ値を抑制。
  - features への書き込みは日付単位で DELETE→INSERT（トランザクション）して原子性を保証（冪等）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して最終スコア final_score を算出し、BUY/SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア:
    - momentum / value / volatility / liquidity / news（AI スコア）
    - 各コンポーネントは欠損時に中立 0.5 で補完。
  - スコア変換: Z スコアをシグモイドで [0,1] に変換するユーティリティを提供。
  - デフォルト重みと閾値: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10、BUY 閾値 0.60。
  - 重みはユーザー入力で上書き可能。入力値の検証と合計が 1.0 でない場合の再スケーリングを実施。無効値は無視してデフォルトにフォールバック。
  - Bear レジーム検知: ai_scores の regime_score 平均が負（かつサンプル数 >= 3）であれば BUY を抑制。
  - エグジット条件（SELL）:
    - ストップロス: 終値 / avg_price - 1 < -8%（最優先）
    - スコア低下: final_score < threshold
    - 保有銘柄の価格欠損時は SELL 判定をスキップして誤クローズを防止。
  - signals テーブルへの書き込みは日付単位の置換（トランザクション）で原子性を保証。
  - いくつかの拡張条件（トレーリングストップ、時間決済）は未実装で、将来実装予定と明記。

- 公開インターフェース
  - strategy パッケージの __all__ に build_features / generate_signals を追加して公開。

### 変更 (Changed)

- 設計方針・実装に関する注記をソース内ドキュメントに多数追加:
  - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用する方針を明確化。
  - DuckDB 操作はトランザクション＋バルク挿入で原子性・性能を意識した実装にしている旨を記載。
  - research モジュールは本番発注 API へアクセスしないことを明記。

### 修正 (Fixed)

- -（初版のため特定のバグ修正履歴はなし。実装上の警告ログやバリデーションにより不整合の早期検出を強化）

### 既知の制限 / TODO

- signal_generator 側で定義されているトレーリングストップ / 時間決済の条件は未実装（positions テーブルに peak_price / entry_date が必要）。将来的に追加予定。
- news_collector の一部の実装方針（INSERT RETURNING による正確な挿入数取得など）は設計に明記されているが、運用上のチューニングや DB スキーマに依存するため追加検証が必要。
- J-Quants クライアントは urllib を使用した実装で、より高度な HTTP 要求（接続プーリング等）を必要とする場合は改善の余地あり。

### 互換性

- 0.1.0 は初期リリースのため破壊的変更はなし。公開 API（関数・クラス・プロパティ）は今後のリリースで変更される可能性があるため、依存する場合はバージョン固定を推奨。

---

今後のリリースでは、モジュール間の結合（execution 層と実際の発注 API の統合）、追加のエグジット条件実装、性能チューニング、テストカバレッジ拡充などを予定しています。