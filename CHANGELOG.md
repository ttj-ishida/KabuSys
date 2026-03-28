CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣例に準拠します。
なお、記載内容は提供されたコードベースの実装から推測して作成しています。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を提供します。
主な追加点・設計上のポイントは以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを実装（kabusys.__init__）。バージョン情報を含む。
  - パッケージ公開 API として data / strategy / execution / monitoring をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応。
  - Settings クラスを提供し、J-Quants, kabuステーション, Slack, DB パス, 実行環境 / ログレベル等をプロパティで取得・バリデーション。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar を用いた営業日判定・前後営業日探索・期間内営業日列挙機能を実装。
    - DB 登録がない場合は曜日ベースのフォールバック（週末は非営業日）を使用。
    - JPX カレンダーの差分取得バッチ（calendar_update_job）を実装。バックフィル／健全性チェックあり。
  - ETL パイプライン (pipeline, etl, etl.ETLResult)
    - ETL 実行結果を格納する ETLResult dataclass を公開。
    - 差分取得・保存・品質チェックの設計に基づくユーティリティを提供（jquants_client と quality モジュールを利用する想定）。
    - DuckDB の状態取得ユーティリティや最大日付取得ロジックを実装。

- 研究・リサーチ (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、Value（PER, ROE）を計算する関数を実装。
    - DuckDB を用いた SQL ベースの実装で外部 API に依存しない設計。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（複数ホライズン、LEAD を利用した実装）、IC（Spearman ρ）計算、統計サマリー、ランク付けユーティリティを実装。
    - pandas 等に依存せず標準ライブラリで処理する設計。

- AI / NLP 機能 (kabusys.ai)
  - ニュースセンチメント (news_nlp.score_news)
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）を用いたバッチ評価で銘柄ごとの ai_score を ai_scores テーブルへ保存。
    - 1銘柄あたりの記事数/文字数制限、バッチサイズ、JSON Mode を用いた応答検証を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの堅牢なバリデーション（JSON 抽出・型検査・未知コード無視）を実装。
    - DuckDB executemany の空リスト制約に配慮した安全な書き込みロジック。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込み。
    - マクロニュースは news_nlp のウィンドウ計算を利用し、OpenAI 呼び出しは独立実装（モジュール結合を避ける）。
    - API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフを実装。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作で行う。

### 変更 (Changed)
- 実装方針（全体）
  - ルックアヘッドバイアス防止のため、各モジュールは内部で datetime.today() / date.today() を不用意に参照せず、target_date を明示的に受け取る設計を採用。
  - DuckDB を主要な分析ストレージとして想定し、SQL+Python で処理を完結する実装に統一。
  - OpenAI 呼び出しは JSON response mode を利用し、応答の堅牢性を高める。

### 修正 (Fixed / Robustness)
- 環境変数読み込み
  - .env 読み込み時に OS 環境変数を保護する protected set を導入し、override 制御で意図しない上書きを防止。
  - .env ファイル読み込み失敗時に警告を出して処理を継続（テストなどでの許容）。
- API 呼び出しの堅牢化
  - OpenAI 呼び出しに対して 429 / ネットワーク断 / タイムアウト / 5xx に対するリトライロジックを追加（指数バックオフ）。
  - API エラーや JSON パース失敗は例外を投げずフォールバック値（macro_sentiment=0.0 やスキップ）で継続することで ETL/集計の頑健性を確保。
- DB 書き込みの安全性
  - market_regime / ai_scores などの書き込みは冪等化（DELETE → INSERT）とトランザクション（BEGIN/COMMIT/ROLLBACK）で実装。ROLLBACK に失敗した場合は警告ログ出力の上再送出。
  - DuckDB executemany に対する空リストバグ回避（空の場合は実行しないガード）を導入。

### セキュリティ (Security)
- 環境変数管理
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動環境読み込みをオフにできる仕組みを提供し、テストや CI 環境での安全性を確保。
  - Settings で必須キー（OpenAI, Slack, Kabu 等）が未設定の場合は明示的に ValueError を送出し、秘密情報の欠如を早期に検出。

### ドキュメント & 設計ノート (Documentation / Notes)
- 各モジュールに詳細な docstring を付与し、処理フロー・設計方針（例: ルックアヘッドバイアス回避、フェイルセーフ、DuckDB 互換性）を明記。
- news_nlp と regime_detector で OpenAI 呼び出し実装を分離し、ユニットテストで _call_openai_api を差し替えやすい設計にしている。

### 既知の制限 (Known issues / Limitations)
- OpenAI（gpt-4o-mini）依存:
  - ニューススコア・レジーム判定は外部 API に依存するため、API キーとネットワークが必要。API の応答フォーマットや料金/レート制限に依存する点に留意。
- 一部の機能（例: jquants_client、quality モジュール、strategy / execution / monitoring の詳細な発注ロジック）は本リリースでのスケッチまたは想定を前提としており、運用前に実装/検証が必要。
- DuckDB バージョン依存:
  - executemany に空リストを渡せない挙動などバージョンによる差異へ対策は講じているが、利用時の DuckDB バージョンによっては追加の互換性確認が必要。

---

将来のリリースでは以下を想定:
- strategy / execution / monitoring の具体的な自動売買ロジックの実装とエンドツーエンドテスト。
- モニタリング・アラート機能（Slack 通知等）の拡充。
- performance 最適化・大規模データでのスケーリング対応。