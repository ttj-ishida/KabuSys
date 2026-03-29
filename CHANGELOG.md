# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
リリース日はパッケージ内のバージョン情報および現行コードベースに基づいて推測しています。

## [Unreleased]
- 次回リリースに向けた改善・追加予定（ドキュメント整備・テストカバレッジ強化・strategy/execution/monitoring 実装の拡充など）

## [0.1.0] - 2026-03-29
初回公開リリース。本バージョンは日本株自動売買システムの基盤機能（データ取得/ETL、マーケットカレンダー管理、リサーチ系ファクター計算、ニュース/マクロのAIスコアリング、環境設定ユーティリティなど）を提供します。

### 追加 (Added)
- パッケージの初期公開
  - パッケージメタ情報: kabusys/__init__.py にて version = 0.1.0 を設定し主要サブパッケージをエクスポート。
- 環境設定/ロード (src/kabusys/config.py)
  - .env/.env.local の自動ロード機能（プロジェクトルートの自動検出: .git または pyproject.toml を基準）。
  - .env ファイルの堅牢なパーサ実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理）。
  - OS 環境変数保護機構（既存の OS 環境変数を保護する protected セット）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを公開し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等の取得メソッドを提供。
  - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値の限定とエラー報告）。
- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - score_news: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（ai_score）を算出し、ai_scores テーブルへ冪等的に書き込む。
  - ニュース時間ウィンドウの計算（JST ベースの定義を UTC naive datetime に変換する calc_news_window）。
  - バッチ処理（最大 20 銘柄／回）、1銘柄あたり記事数・文字数のトリム制御、JSON Mode レスポンスの堅牢なバリデーション、スコアの ±1 クリップ。
  - API の 429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライ処理と、失敗時はスキップして処理を継続するフェイルセーフ設計。
  - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
  - DuckDB の executemany に関する注意（空リストの禁止）に対応した安全な書き込みロジック（DELETE → INSERT）。
- マーケットレジーム判定 (src/kabusys/ai/regime_detector.py)
  - score_regime: ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して当該日の市場レジーム（bull/neutral/bear）を算出・market_regime テーブルに冪等書き込み。
  - ma200_ratio 計算は target_date より前のデータのみ使用しルックアヘッドを防止。
  - マクロニュース抽出（キーワードリストを使用）、OpenAI 呼び出し（gpt-4o-mini）で JSON 出力を解析。
  - API 呼び出しのリトライ/エラー処理と、API 失敗時に macro_sentiment=0.0 として継続するフェイルセーフ。
  - テスト用に _call_openai_api の差し替えを容易に実装。
- データプラットフォーム / カレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX カレンダー用ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
  - market_calendar テーブル有無に応じた挙動（DB 登録があれば DB 優先、未登録日は曜日ベースでフォールバック）。
  - calendar_update_job: J-Quants API からの差分取得と market_calendar テーブルへの冪等保存、バックフィルと健全性チェックを実装。
  - 最大探索日数制限や未来日付の健全性チェックを導入して無限ループや予期せぬデータを防止。
- ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult データクラスを導入し ETL の成果（取得数／保存数／品質問題／エラー）を構造化して返却。
  - 差分更新・バックフィル・品質チェック方針に基づいた ETL の基盤ユーティリティを実装。
  - etl モジュールで ETLResult を公開再エクスポート。
- リサーチ（ファクター計算 / 特徴量探索）(src/kabusys/research/*.py)
  - factor_research: calc_momentum（1M/3M/6M リターン、ma200 乖離）、calc_volatility（20日 ATR、流動性指標）、calc_value（PER, ROE）を実装。
  - feature_exploration: calc_forward_returns（複数ホライズンの将来リターン計算）、calc_ic（スピアマンランク相関による IC）、rank（同順位平均ランク）、factor_summary（基本統計量）を実装。
  - いずれも DuckDB 接続を受け取り、外部 API へのアクセスを行わない安全設計。
  - research.__init__ で主要関数をまとめてエクスポート。
- 公開 API と設計方針ドキュメント的コメント
  - 各モジュールに設計方針・処理フロー・フェイルセーフの注釈（ルックアヘッドバイアス防止、部分失敗保護、DuckDB 互換性など）を詳細に記載。

### 変更 (Changed)
- （初回リリースのため該当なし。将来のリリースで API の破壊的変更や最適化を記載予定）

### 修正 (Fixed)
- .env パーサの堅牢化（export 句、クォート内のエスケープ処理、コメント判定の改善）により環境変数の読み込みに関する多くのケースをサポート。
- OpenAI API 呼び出しに対するリトライ／例外ハンドリングを整備（RateLimit / 接続エラー / タイムアウト / 5xx の扱いを明確化）。
- DuckDB に対する書き込み処理での executemany 空リスト問題に対応する安全な実装。

### セキュリティ (Security)
- 環境変数取得時に必須項目が未設定の場合は明確な ValueError を送出（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY のチェックロジック）。
- ログレベル・環境種別のホワイトリスト検証（不正な値を弾く）。

### 注意点 / 既知の制約 (Notes / Known issues)
- OpenAI 依存箇所（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とする。キー未設定時は呼び出しが ValueError で失敗する設計。
- JSON Mode を使うが稀に前後に余計なテキストが混在するケースを想定して復元ロジックを組み込んでいるが、LLM 出力の想定外フォーマットによりスコア取得が失敗する可能性がある（その場合は該当チャンクをスキップ）。
- DuckDB のバージョン差異に起因するバインド/型挙動（list バインドや executemany の空リスト）は実運用時に注意。コード中に互換性対策を含めている。
- calendar_update_job / pipeline の外部 API 呼び出し（J-Quants）失敗時は例外をキャッチして 0 を返す設計になっているため、呼び出し元での監視/再試行が必要。

---

作成した CHANGELOG はコード中の docstring・設計注記・明示的な挙動から推測して構成しています。必要であれば、各項目をより詳細に分割（例: モジュール別に例や使用例を追記）したり、リリース日を修正したりできます。どの程度の粒度で記載するか指示をいただければ追記します。