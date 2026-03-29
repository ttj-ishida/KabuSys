# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このファイルは、コードベース（src/kabusys/...）の内容から実装された機能・設計方針を推測して作成しています。

## [0.1.0] - 2026-03-29

### 追加 (Added)
- パッケージ初期リリース: KabuSys — 日本株自動売買支援ライブラリ
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - .env パーサを実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - OS 環境変数の保護（.env の上書きを制御）をサポート。
  - 自動読み込みの無効化フラグ (KABUSYS_DISABLE_AUTO_ENV_LOAD) を提供。
  - Settings クラスを実装してアプリケーション設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / DB（DuckDB / SQLite）等の主要設定を提供。
    - KABUSYS_ENV の検証（development / paper_trading / live）と LOG_LEVEL の検証。

- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news と news_symbols を元に、銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - バッチ処理: 1呼び出しあたり最大 20 銘柄、1銘柄あたり最大 10 件・3000 文字にトリム。
    - OpenAI JSON Mode を使用し、レスポンスのバリデーションと復元ロジックを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装（最大リトライ回数は定数で管理）。
    - スコアは ±1.0 にクリップ。失敗時はフェイルセーフでスキップし他銘柄処理を継続。
    - DuckDBへの書き込みは冪等（DELETE → INSERT）で、部分失敗時に既存データを守る実装（executemany の空リスト問題への対応あり）。
    - テスト容易性を考慮し、OpenAI呼び出し関数をモック置換できる（_call_openai_api の差し替え）。

  - 市場レジーム判定 (ai.regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定・保存。
    - データ取得は DuckDB の prices_daily / raw_news を参照。lookahead バイアス防止設計（target_date 未満のデータのみ使用、datetime.today() を直接参照しない）。
    - OpenAI 呼び出しは独立実装で、API エラーに対するリトライ / フェイルセーフを備える。
    - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保。失敗時は ROLLBACK を試行。

- データ基盤ユーティリティ (kabusys.data)
  - 市場カレンダー管理 (data.calendar_management)
    - market_calendar テーブルの参照・更新ロジックと営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダー情報が無い場合の曜日ベースフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得→保存の夜間バッチを実装（バックフィル・健全性チェック含む）。
    - 最大探索日数および不変条件で無限ループを防止。

  - ETL パイプライン (data.pipeline, data.etl)
    - ETLResult データクラスを公開して ETL 実行結果を集約（取得数・保存数・品質問題・エラー等）。
    - ETL の設計方針に沿った差分更新・バックフィル・品質チェックの枠組みを実装（jquants_client と quality モジュールに依存）。
    - DuckDB の存在チェック・最大日付取得ユーティリティを実装。

- リサーチ／因子計算 (kabusys.research)
  - factor_research:
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR 等）、Value（PER / ROE）を DuckDB の SQL で計算する関数を実装。
    - データ不足時の None ハンドリングや、スキャン範囲のバッファ設計を実装。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン）calc_forward_returns
    - IC（スピアマンランク相関）calc_ic、ランク関数 rank、統計サマリー factor_summary を実装。
    - pandas 等の外部依存を使わず標準ライブラリのみで実装。

- 汎用・設計
  - DuckDB を主要なローカル分析用 DB として利用。
  - 外部 API 呼び出し（OpenAI / J-Quants）は API キーを引数で注入可能（テスト容易性）。
  - ロギング（logger）による詳細な情報・警告出力を多数実装し、障害診断を容易に。

### 変更 (Changed)
- 初回リリースのため該当なし（新規追加中心）。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制限 (Notes / Known limitations)
- OpenAI API キーが未設定の場合、score_news / score_regime は ValueError を送出する（明示的に鍵を渡すか環境変数 OPENAI_API_KEY を設定する必要あり）。
- ai モジュールは gpt-4o-mini を想定。将来のモデルや SDK バージョン変更に対してはレスポンス処理／エラー判定（status_code など）で互換性対策を行っているが、SDK仕様変更時の追加対応が必要になる可能性あり。
- DuckDB の executemany が空リストを許容しない点に対応済み（空チェックを行う）だが、使用する DuckDB バージョン依存の挙動に注意。
- 外部モジュール（jquants_client, quality など）は別実装を想定しており、実運用前にそれらの実装・設定が必要。
- ルックアヘッドバイアス対策として datetime.today()/date.today() を直接使わない設計を採用。ETL/スコアリング関数は target_date を明示的に受け取る。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

開発者向けメモ:
- テストでは環境読み込みを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用すると安全。
- OpenAI 呼び出し部分はモック可能（kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api）でユニットテストが容易。
- DuckDB 接続を作成して target_date を指定することで deterministic に処理を再現できます（ルックアヘッド防止のため日付取得は外部化）。

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノートはリリース時の変更差分に基づいて更新してください。）