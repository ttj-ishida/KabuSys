# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。互換性のあるバージョニングを採用しています。

なお、本ファイルはリポジトリ内のソースコードから推測して作成した初期の変更履歴です（自動生成ではなくコード内容に基づく記述）。必要に応じて日付や詳細を編集してください。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース

### 追加 (Added)
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml による検出）から自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - export KEY=val 形式やクォート／エスケープ／インラインコメント等に対応するパーサ実装。
  - 必須環境変数未設定時に ValueError を送出する _require()。例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（OpenAI キーは個別モジュールでチェック）。
  - 設定項目のプロパティを提供（例: duckdb_path, sqlite_path, pid_file_path, CPU/メモリ/ディスク閾値、KABUSYS_ENV, LOG_LEVEL）。KABUSYS_ENV と LOG_LEVEL は値検証を行う。
  - OS 環境変数を保護するための protected set を考慮して .env の上書きを制御。

- AI 関連機能 (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news / news_symbols を入力に、OpenAI（gpt-4o-mini）を用いた銘柄単位のニュースセンチメントスコアリング機能 (score_news) を実装。
    - ニュースの時間ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST を UTC で比較する calc_news_window を提供。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、1 銘柄あたり最大記事数／文字数のトリムを実装。
    - JSON Mode（厳密な JSON 出力）を前提とし、レスポンスの堅牢なパース／バリデーション実装（途中の余計なテキスト混入に対する復元処理含む）。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライ。その他エラーは安全にスキップして処理継続（フェイルセーフ）。
    - DuckDB 互換性のため、executemany に空リストを渡さない保護ロジックを実装。
    - テスト容易性のため OpenAI 呼び出し箇所（_call_openai_api）をモック可能に設計。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定する score_regime 実装。
    - makro キーワードで raw_news のタイトルを抽出し、OpenAI（gpt-4o-mini）によりマクロセンチメントを評価。
    - API エラー時には macro_sentiment=0.0 でフォールバックする設計（例外を上げず継続）。
    - 出力は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行のうえ例外伝播。
    - lookahead バイアスを避けるため、target_date 未満のデータのみを利用し、datetime.today() などは参照しない設計。

- データ関連ユーティリティ (kabusys.data)
  - 市場カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）実装。J-Quants クライアント経由で取得・保存を行い、バックフィルや健全性チェックを備える。
    - 営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。market_calendar が未取得のときは曜日ベースのフォールバック（週末を非営業日と見なす）。
    - DB 登録値優先、未登録日は曜日フォールバックとして一貫した挙動を提供。

  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを公開（target_date、取得／保存件数、品質問題、エラー一覧など）。
    - 差分更新、バックフィル、品質チェックの設計方針を反映した基盤処理の下地を実装（jquants_client と quality モジュールによる保存・検査を想定）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高変化率）、バリュー（PER、ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB を用いた SQL ベースの実装、データ不足時の None ハンドリング、ログ出力を実装。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン）、ランク相関（Spearman）を用いた IC 計算 calc_ic、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存しない純粋な実装。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- （初版のため該当なし）

### 内部（設計上の重要点・注意事項）
- 外部 API（OpenAI / J-Quants）呼び出しは堅牢化（リトライ・バックオフ・フォールバック値）されており、API 失敗によってプロセス全体が停止しないよう設計されています。
- Lookahead バイアス防止: 日付参照は target_date を明示的に使用し、datetime.today()/date.today() を参照しない箇所を多く採用（AI スコア・レジーム判定・ニュースウィンドウ等）。
- DuckDB 互換性: executemany に空リストを渡すと問題となるバージョンに対する防御コードを追加。
- OpenAI 呼び出し部はテストで差し替え可能（ユニットテストが容易）。
- AI モデルおよび JSON Mode を前提としてプロンプト設計（厳密な JSON 出力を期待）。レスポンスは厳密にバリデートし、誤った出力はスキップして安全側に倒す。
- .env の読み込みはプロジェクトルートを基準に行うため、CWD に依存しない（パッケージ配布後も安定）。

### 必要な環境変数（代表例）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI 呼び出し用（score_news / score_regime で必須）
- KABUSYS_ENV: development / paper_trading / live（検証あり）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等はデフォルト値が設定されており、必要に応じてオーバーライド可能

---

この CHANGELOG はコードからの推測に基づくため、実際のコミット履歴やリリースノートと差異がある可能性があります。必要に応じて日時・影響範囲・導入手順等を追記してください。