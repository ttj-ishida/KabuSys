# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトでは Keep a Changelog の仕様に従い、セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-31

初回公開リリース。

### 追加 (Added)
- パッケージ初期構成を追加
  - パッケージ名: kabusys（src/kabusys）
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env/.env.local の読み込み順序: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - export KEY=val 形式、クォートやエスケープ、インラインコメントの考慮など堅牢なパース実装。
  - 必須環境変数取得用 _require() と Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN など多数の設定プロパティ）。
  - 環境値検証: KABUSYS_ENV と LOG_LEVEL の許容値チェック。
- AI（自然言語処理）モジュール (src/kabusys/ai)
  - ニュースセンチメントスコアリング (score_news)
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメントを ai_scores テーブルへ書き込む。
    - バッチサイズ、記事数上限、文字数トリム等のトークン肥大化対策を実装。
    - JSON Mode を期待し、レスポンスの厳密バリデーションとクリッピング（±1.0）を行う。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - API 呼び出しを差し替え可能にするフック（テスト用の patch ポイント）を用意。
    - ルックアヘッドバイアスを避けるため、datetime.today() を直接参照しない設計。
  - 市場レジーム判定 (score_regime)
    - ETF（1321）の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して market_regime に保存。
    - マクロニュース抽出のキーワードリスト、LLM 呼び出し、リトライ、フォールバック（失敗時は macro_sentiment=0.0）を実装。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）で上書き。
- データ処理モジュール (src/kabusys/data)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar を元に営業日判定、next/prev_trading_day、get_trading_days、is_sq_day 等のユーティリティを提供。
    - DB 未登録日は曜日ベースのフォールバック（週末除外）。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェックの実装。
  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを導入（取得件数／保存件数／品質問題／エラーの集約）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）の設計に準拠した処理フローの骨組みを実装。
    - DuckDB の互換性問題（executemany に空リスト不可）を考慮した実装。
  - jquants_client を通じたデータ取得・保存インタフェースを参照（実装は jquants_client 側）。
- 研究／リサーチ機能 (src/kabusys/research)
  - factor_research モジュール
    - calc_momentum：1M/3M/6M リターン、200日 MA 乖離の計算。
    - calc_volatility：20日 ATR、ATR比率、20日平均売買代金、出来高比率。
    - calc_value：PER（EPS 判定あり）、ROE の計算（raw_financials と prices_daily を結合）。
    - 計算は DuckDB SQL を活用し、対象テーブルのみ参照する安全設計。
  - feature_exploration モジュール
    - calc_forward_returns：指定ホライズンの将来リターンを一括で取得。
    - calc_ic：Spearman（ランク）相関による IC 計算（3件未満は None）。
    - rank：同順位は平均ランク扱いのランク化ユーティリティ（丸めによる ties 対応）。
    - factor_summary：count/mean/std/min/max/median の統計サマリ。
- パッケージエクスポート整理
  - ai, data, research パッケージの __init__ による主要 API の再エクスポートを整備。

### 変更 (Changed)
- 設計方針や実装上の注意点を多数の docstring とログに明記（ルックアヘッドバイアス対策、DuckDB 互換性、フェイルセーフ挙動など）。

### 修正 (Fixed)
- API レスポンスの不正（JSON パース失敗、余分な前後テキスト混入）に対する復元ロジックを追加（news_nlp._validate_and_extract）。
- OpenAI SDK の例外仕様差異に対する堅牢化（APIError の status_code 取得を getattr で安全に扱う）。

### 注意点 / 既知の制約 (Known issues / Notes)
- OpenAI API キーは必須（score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を要求し、未設定時は ValueError を送出）。
- DuckDB を利用するため、実行環境に duckdb パッケージが必要。
- news_nlp と regime_detector は gpt-4o-mini（OpenAI）を想定した JSON Mode を前提に実装している。
- 時刻・ウィンドウは UTC naive datetime を使う設計（news ウィンドウは JST を UTC に変換して比較しているため、DB の datetime は UTC で保存されている前提）。
- 一部の計算は過去データ不足時に None を返す（例: MA200 未満のデータなど）。
- jquants_client と quality モジュールは外部依存（連携実装が必要）。

### セキュリティ (Security)
- 環境変数の読み込みでは OS 環境変数を保護する機構（protected set）を採用し、.env による上書きの際に意図しない上書きを防止。

---

今後のリリースでは、発注（execution）や監視（monitoring）モジュールの詳細実装、テストカバレッジ強化、OpenAI 呼び出しの抽象化やローカル代替器の導入などを予定しています。