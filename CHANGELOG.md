# Changelog

全ての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初回リリース。

### 追加 (Added)
- パッケージ基本構成
  - kabusys パッケージの公開モジュール: data, strategy, execution, monitoring（src/kabusys/__init__.py）
  - バージョン: 0.1.0

- 環境設定/ローダー (src/kabusys/config.py)
  - .env ファイルと環境変数を統合して読み込む自動ローダーを実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パースの強化:
    - export KEY=val 形式をサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（引用あり/なしでの挙動差異）
  - Settings クラスを導入し、主要な設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH, SQLITE_PATH（Path を返す）
    - 環境種別: KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

- データプラットフォーム関連 (src/kabusys/data/)
  - ETL パイプラインインターフェースと結果型:
    - ETLResult dataclass（pipeline の公開インターフェースを再エクスポート）
    - ETLResult.to_dict() で品質問題をシリアライズ可能
  - pipeline モジュール（差分取得・保存・品質チェックの設計）
    - 差分更新、バックフィルのデフォルト（3日）などを定義
    - DuckDB を想定したテーブル存在チェックと最大日付取得ユーティリティ
  - calendar_management モジュール
    - JPX カレンダーの夜間更新ジョブ calendar_update_job を実装（J-Quants client 経由で差分取得・保存）
    - 営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - 設計: DB データが無い/未登録日には曜日ベースのフォールバックを使用。最大探索範囲で無限ループ防止。

- 研究 (research) モジュール (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率
    - calc_value: PER（EPS が 0/未設定 の場合は None）、ROE（raw_financials から取得）
    - DuckDB SQL + Python での実装（prices_daily / raw_financials を参照）
  - 特徴量探索 (feature_exploration.py)
    - calc_forward_returns: 任意ホライズンに対する将来リターン（デフォルト: [1,5,21]）
    - calc_ic: Spearman（ランク相関）での IC 計算（3 レコード未満は None）
    - rank: 同順位は平均ランクにするランク関数（浮動小数点丸めで ties 対策）
    - factor_summary: count/mean/std/min/max/median を算出（None を除外）

- AI / NLP 機能 (src/kabusys/ai/)
  - ニュース NLP (news_nlp.py)
    - score_news(conn, target_date, api_key=None):
      - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（内部は UTC naive datetime で計算）
      - news_symbols と raw_news を集約して銘柄ごとに記事をまとめ、最大 20 銘柄ずつバッチで OpenAI (gpt-4o-mini) に送信
      - JSON モードでのレスポンス検証・スコアの ±1.0 クリップ
      - リトライ: レート制限・ネットワーク・タイムアウト・5xx に対し指数バックオフ
      - DB 書き込みは部分失敗を考慮して該当コードのみ DELETE→INSERT（DuckDB executemany の空リスト回避ロジックあり）
  - 市場レジーム判定 (regime_detector.py)
    - score_regime(conn, target_date, api_key=None):
      - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
      - マクロキーワードで raw_news をフィルタ、最大 20 記事を LLM 判定に使用
      - OpenAI 呼び出しは専用の内部実装。API 失敗時は macro_sentiment = 0.0（フェイルセーフ）
      - レジームスコアを clip(-1, 1) した上で label を bull / neutral / bear に分類
      - market_regime へ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）

- DuckDB を中心としたデータ操作
  - 各モジュールは DuckDB の接続オブジェクトを受け取り、SQL と Python の組合せで計算／書き込みを行う設計
  - 日付取り扱いはすべて date オブジェクトで統一（timezone の混入を避ける方針）

### 変更 (Changed)
- 初版のため該当なし

### 修正 (Fixed)
- 初版のため該当なし

### 破壊的変更 (Breaking Changes)
- 初版のため該当なし

### セキュリティ (Security)
- OpenAI / 外部 API・Slack・kabu API の API キーは環境変数で必須（Settings._require により未設定時は ValueError を送出）。
- .env 自動ロードによりローカルでの鍵管理を容易にする一方、実運用では機密情報の取り扱いに注意。

---

使用例（抜粋）
- 環境設定:
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path など

- ニューススコア付与:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)

- 市場レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)

- 研究用ファクター:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - calc_momentum(conn, target_date)

フィードバックやバグ報告は issue を立ててください。