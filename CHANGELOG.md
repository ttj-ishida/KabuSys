# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在の日付: 2026-03-28

## [0.1.0] - 2026-03-28
初回リリース — 日本株自動売買 / データ基盤 / リサーチ用ユーティリティの基本実装を追加。

### 追加（Added）
- パッケージ基盤
  - 基本パッケージ定義とバージョンを追加（kabusys.__version__ = 0.1.0）。
  - パッケージ外部公開シンボルを整理（kabusys.__all__ に data, strategy, execution, monitoring を公開）。

- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化が可能。
  - .env パースの堅牢化: export 付き行、シングル/ダブルクォート対応、エスケープ処理、インラインコメント判定等を実装。
  - 必須設定の取得用 _require と Settings のプロパティ群を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境値のバリデーション（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント分析（news_nlp.score_news）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - チャンク処理（デフォルト 20 銘柄/チャンク）、1 銘柄あたり最大記事数・文字数制限（トリム）を実装。
    - レスポンス検証ロジックを実装（JSON 抽出、results 配列検査、コード照合、数値変換、スコア ±1.0 クリップ）。
    - 失敗時は個別チャンクをスキップして継続するフェイルセーフ（API 429/ネットワーク/5xx はリトライ、その他はスキップ）。
    - DuckDB への冪等書き込み（対象 code のみ DELETE → INSERT）を実装。部分失敗時に既存データを保護。
    - テスト容易性のため _call_openai_api を patch 可能とした設計。
    - calc_news_window による JST 時刻ウィンドウ計算（前日15:00〜当日08:30 JST の扱い）を提供。

  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して market_regime に書き込み。
    - マクロニュース抽出（マクロキーワードによるフィルタ）と OpenAI 呼び出し（gpt-4o-mini）を実装。
    - リトライ・バックオフ・API 例外ハンドリングを実装。API 失敗時のフォールバック（macro_sentiment = 0.0）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を試行して例外を上位へ伝播。

- データモジュール（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合の曜日ベースフォールバックを採用（週末は非営業日）。
    - 夜間バッチ更新 job（calendar_update_job）を実装：J-Quants API から差分取得 → 保存（jq.fetch_market_calendar / jq.save_market_calendar） → バックフィル / 健全性チェック。
    - 探索範囲上限（_MAX_SEARCH_DAYS）による無限ループ防止。

  - ETL / パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（ETLの実行結果・品質問題・エラーの集約）。
    - 差分取得、バックフィル、品質チェック、保存（idempotent 保存）を行う ETL パイプライン設計に対応する基盤コードを実装。
    - jquants_client と quality モジュールを利用するインターフェースを想定。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算（research.factor_research）
    - モメンタム（1M/3M/6M）、200日移動平均乖離、20日 ATR（atr_20）、平均売買代金、出来高指標、PER/ROE（raw_financials からの最新データ）などを DuckDB 経由で算出する関数群を実装。
    - データ不足時の None 扱い、SQL とウィンドウ関数中心の実装。
  - 特徴量探索（research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意 horizon に対応、入力バリデーションあり）。
    - IC（Information Coefficient）計算（calc_ic: Spearman ランク相関の実装、必要最小サンプルチェック）。
    - ランク付けユーティリティ（rank）とファクター統計要約（factor_summary）を実装。
  - いくつかのユーティリティを top-level に再エクスポート（zscore_normalize 等）。

### 変更（Changed）
- 初期公開のための API 設計・命名が確定（関数名・引数・戻り値の仕様を明示）。
- DuckDB を主なデータストレージとして想定した SQL 実装に調整。

### 修正（Fixed）
- （初版のため該当なし。実装上の堅牢性確保のため、各所でエラー時のフォールバックやログ出力を強化。）

### セキュリティ（Security）
- OpenAI の API キーは関数引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を返して誤動作を防止。
- .env 自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### 設計上の重要な注意点（Notes）
- ルックアヘッドバイアス防止: 全てのスコアリング / リサーチ関数は datetime.today() / date.today() を参照せず、呼び出し元が target_date を明示して与える設計。
- フェイルセーフ: API の一時障害や不整合レスポンスが発生しても例外で処理全体を停止させず、可能な範囲で継続することを優先して実装（ログ出力してフォールバック値を使用）。
- DuckDB 互換性: executemany に空リストを渡せない既知挙動（DuckDB 0.10）を考慮し、空チェックを行ってから executemany を呼ぶ実装にしている。
- テスト容易性: OpenAI 呼び出し部分はモック差替えしやすいよう個別関数で囲んでいる（例: _call_openai_api の patch）。

### 既知の制限・未実装（Known issues / TODO）
- Strategy / execution / monitoring パッケージの具体的な実装は本バージョンでは含まれていない（パッケージ公開用に __all__ に記載）。
- 一部の指標（PBR・配当利回り等）は未実装（calc_value に注記あり）。
- jquants_client / quality モジュールの具体的実装はここでは参照箇所のみで詳細実装は別途。

---

今後のリリースでは以下を予定：
- production 向けの発注・戦略実装（execution / strategy）。
- モデル・プロンプトの微調整、スコア検証・評価パイプライン。
- テストカバレッジの拡充と CI パイプライン整備。