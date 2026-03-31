# Keep a Changelog — CHANGELOG.md（日本語）

すべての変更は https://keepachangelog.com/ja/ に従って記載しています。

全般的な方針：
- バージョン付けは package の __version__（0.1.0）に準拠。
- 実装内容はソースコードから推測して記載しています（実際のコミット履歴ではありません）。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムのコア機能群を実装しました。主な追加・設計上の注記は以下のとおりです。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージ初期実装。公開 API（__all__）に data, strategy, execution, monitoring を用意。
  - バージョン情報: __version__ = "0.1.0"。

- 環境・設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定自動読み込みを実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - .env のパースロジックを詳細実装（コメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント判定などに対応）。
  - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ対応（テスト用途）。
  - 設定取得用 Settings クラスを追加。J-Quants / kabuステーション / Slack / DB / 監視 / システム関連のプロパティを定義（必須項目は _require で検証）。
  - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の値検証を実装。

- データ（data）
  - ETL パイプラインインターフェース（kabusys.data.pipeline.ETLResult）を追加し、kabusys.data.etl から再エクスポート。
  - calendar_management モジュールを追加：
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - calendar_update_job: J-Quants からの差分取得・バックフィル・保存（冪等）ロジック。
    - DB データがない/欠損時の曜日フォールバックや最大探索日数制限など、堅牢性のための設計を導入。
  - ETL パイプライン（kabusys.data.pipeline）を追加：
    - 差分取得、保存（idempotent 保存）、品質チェック連携のための骨格を実装。
    - ETLResult データクラスを提供（品質問題・エラーの集約・辞書化メソッドを実装）。
    - DuckDB との互換性や空リスト executemany の回避などの実装上の配慮を含む。

- 研究（research）
  - factor_research モジュールを追加：
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を算出（EPS 欠損時は None）。
    - DuckDB を用いた SQL + Python による実装。ルックアヘッドバイアス回避を考慮。
  - feature_exploration モジュールを追加：
    - calc_forward_returns: 将来リターン（デフォルト [1,5,21]）を一度のクエリで取得する実装。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク相関）を計算（レコード不足時は None）。
    - rank / factor_summary: ランク化（同順位は平均ランク）と基本統計量サマリを実装。
  - research パッケージ __init__ で主要関数を再エクスポート。

- AI（kabusys.ai）
  - news_nlp モジュール（score_news）を追加：
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini / JSON mode）にバッチ送信してスコアを算出。
    - チャンクサイズ、1銘柄あたりの最大記事数・文字数制限、タイムウィンドウ（JST 前日15:00〜当日08:30）などを実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実施。レスポンス検証と数値クリップ（±1.0）。
    - DuckDB への書き込みは、部分失敗時に既存スコアを保護するため対象コードのみ DELETE→INSERT で置換。
  - regime_detector モジュール（score_regime）を追加：
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM, 重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で算出・保存。
    - raw_news をマクロキーワードでフィルタして LLM 呼び出し（gpt-4o-mini / JSON mode）を行う。API 失敗時は macro_sentiment=0.0 をフォールバック。
    - レジームの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - AI モジュールは OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。テスト用に _call_openai_api を差し替え可能な設計。

- その他ユーティリティ / 実装上の配慮
  - DuckDB を前提とした SQL クエリ実装（prices_daily / raw_news / raw_financials / ai_scores / market_regime 等を参照）。
  - ルックアヘッドバイアス回避のため、内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示で渡す）。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）の適切な取り扱いと例外時のフォールバックログ。
  - OpenAI 呼び出しでのレスポンスパース失敗・部分不整合に対しログを残し安全にフォールバックする実装。
  - 型注釈（PEP 484）や詳細な docstring によるセルフドキュメント化。

### 変更 (Changed)
- 初期リリースのため過去バージョンからの変更点はありません（新規追加）。

### 修正 (Fixed)
- 初期リリースのため過去バージョンからの修正点はありません。

### 非推奨 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

### セキュリティ (Security)
- 環境変数の取り扱いに注意：
  - 必須トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は Settings で必須チェックを行い、未設定時は ValueError を発生させる仕様。
  - 自動 .env 読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD により、テストや CI 環境での誤読を防止可能。
  - OpenAI API の呼び出し結果は外部依存のため、失敗時は中立スコアにフォールバック（例外を破壊的に波及させない）して安全性を確保。

### 既知の制限・注意事項
- OpenAI（gpt-4o-mini）を利用する機能は API キーが必要。キー未設定だと score_news / score_regime は ValueError を送出します。
- DuckDB のバージョン差異（executemany の空リストバインド挙動など）に配慮した実装がされていますが、実行環境の DuckDB バージョンにより挙動が異なる可能性があります。
- news_nlp や regime_detector は LLM の出力を厳密な JSON として期待する設計ですが、実際のレスポンスのノイズを吸収するために追加のパース/サニタイズ処理を実装しています。完全な安定性は LLM の挙動に依存します。
- monitoring モジュールのエクスポートは宣言されていますが（__all__ に含まれる）、この変更セットに該当するモジュールの具象実装が含まれていない場合があります（将来的に追加予定）。

---

将来的なリリースでは以下のような項目が想定されます（例）:
- strategy / execution / monitoring の具体実装の追加・統合テスト
- J-Quants / kabu API クライアントの詳細実装・認証フロー
- 性能改善、並列処理、テストカバレッジの向上
- セキュリティレビュー（機密情報の取り扱い）および運用ドキュメントの充実

（以上）