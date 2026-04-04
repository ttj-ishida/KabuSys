# Changelog

すべての重要な変更をこのファイルに記載します。  
このプロジェクトでは "Keep a Changelog" の形式に従い、セマンティックバージョニングを採用しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ修正

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。日本株のデータ収集・ETL・ファクター算出・ニュースNLP・市場レジーム判定を行う基盤機能を実装。

### Added
- パッケージ基本構成
  - kabusys パッケージの公開モジュールを定義（data, strategy, execution, monitoring）。
  - バージョン定義: `__version__ = "0.1.0"`。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み順序: OS環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - .env のパースは export 形式、クォート、インラインコメント、エスケープに対応。
  - Settings クラスでアプリ設定をプロパティとして提供（J-Quants トークン、kabu API パスワード、LINEトークン、DBパス、監視閾値、環境モード等）。
  - 必須変数の未設定時は明示的な ValueError を送出。

- AI ニュース解析（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄毎のセンチメントスコア（-1.0〜1.0）を算出、ai_scores テーブルへ書き込み。
  - ニュース集計ウィンドウ（JST 前日15:00〜当日08:30）を計算するユーティリティ `calc_news_window` を提供。
  - バッチ処理（最大20銘柄/リクエスト）、1銘柄あたりの記事・文字数上限によるトークン肥大化対策。
  - JSON Mode での応答整形・バリデーション実装（結果の検証、未知コードの無視、スコアのクリップ）。
  - API 呼び出しに対する指数バックオフと再試行（429 / ネットワーク断 / タイムアウト / 5xx）を実装。
  - API失敗やパース失敗はフェイルセーフでスキップし、部分成功時は既存の他銘柄スコアを保護するため対象コードのみ置換（DELETE→INSERT）。

- AI 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定、market_regime テーブルへ冪等書き込み。
  - DuckDB からの過去データ参照はルックアヘッドバイアスを防ぐ（target_date 未満のみ使用）。
  - マクロキーワードによるニュース抽出、OpenAI 呼び出しの再試行・フェイルセーフ（API失敗時 macro_sentiment=0.0）。
  - OpenAI 呼び出し部分はテスト用に差し替え可能に設計（モック利用）。

- 研究用ファクター計算（kabusys.research）
  - calc_momentum: 1ヶ月/3ヶ月/6ヶ月リターン、200日MA乖離を計算。
  - calc_volatility: 20日ATR、相対ATR、20日平均売買代金、出来高比率を計算。
  - calc_value: raw_financials の直近財務データと日次株価を使って PER / ROE を計算。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）等を提供。
  - DuckDB 接続を受け、prices_daily / raw_financials テーブルのみ参照することで、発注系API等には一切アクセスしない設計。

- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。DB 登録がない日は曜日ベースでフォールバック。
  - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックを含む）。
  - pipeline / etl: ETLResult データクラスによる ETL 実行結果の集約、差分取得 → 保存 → 品質チェックの設計に対応。jquants_client 経由での idempotent 保存を想定。
  - etl モジュールで ETLResult を再エクスポート。

### Notable design decisions / 保証事項
- ルックアヘッドバイアス防止:
  - AI スコアリング・レジーム判定・ファクター計算はいずれも内部で datetime.today()/date.today() を直接参照せず、引数で与えた target_date 未満／以前のデータのみを使用するよう設計。
- DB 書き込みは冪等化:
  - market_regime / ai_scores 等への書き込みは DELETE → INSERT または ON CONFLICT 相当の方法で既存データを置換し、部分失敗時に無関係な既存データを消さない工夫あり。
- フェイルセーフ性:
  - 外部 API（OpenAI, J-Quants）でのエラーは再試行/バックオフやログ出力の上で部分スキップし、プロセス全体を停止させない設計。
- テスト容易性:
  - OpenAI 呼び出し関数はモジュール内でラップされており、ユニットテスト時に patch して差し替え可能。
- DuckDB ベース:
  - データ処理は DuckDB 接続を前提とし、SQL + Python の組合せで実装。

### Files / Public API highlights
- src/kabusys/__init__.py: パッケージ公開要素定義
- src/kabusys/config.py: Settings クラス、自動 .env ロード、解析ユーティリティ
- src/kabusys/ai/news_nlp.py: calc_news_window, score_news（OpenAI 経由のニュースNLP）
- src/kabusys/ai/regime_detector.py: score_regime（市場レジーム判定）
- src/kabusys/research/*: calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, rank, factor_summary
- src/kabusys/data/calendar_management.py: カレンダー管理・営業日判定・calendar_update_job
- src/kabusys/data/pipeline.py: ETLResult 等、ETL パイプライン補助

### Known limitations / 注意点
- OpenAI SDK / ネットワークのレート制限によりリクエスト失敗が発生する可能性があり、結果が得られない銘柄はスキップされる（部分的な書込みで既存データを保護する設計）。
- DuckDB のバージョン依存の挙動（list 型バインド等）を考慮した実装（executemany の空リスト回避など）を行っているが、異なる DuckDB バージョンでの動作確認は必要。
- 現バージョンで PBR や配当利回り等のバリュー指標は未実装。

### Required / Recommended environment variables
- OPENAI_API_KEY (または score_* 関数への api_key 引数)
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- その他（オプション）: KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等

---

今後の予定（例）
- strategy / execution / monitoring の実装拡張（現状はパッケージ構成のみ公開）。
- 追加のファクターやポートフォリオ構築機能、より高度な品質チェックの導入。
- テストカバレッジの充実と CI ワークフローの整備。

---