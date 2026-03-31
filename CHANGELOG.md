KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
リリース日付はコードベースのスナップショットから推測して記載しています。

[Unreleased]
- 開発中の変更はここに記載します。

[0.1.0] - 2026-03-31
Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、バージョン 0.1.0
  - main export: kabusys モジュールは data, strategy, execution, monitoring サブパッケージを公開。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local を自動読み込み（優先順: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出は __file__ から親ディレクトリを探索し .git / pyproject.toml を基準に行うため CWD に依存しない実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメント処理など多くのケースに対応。
  - Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境名 / ログレベル 等のプロパティ）。未設定の必須変数は _require() により ValueError を投げる。
  - KABUSYS_ENV と LOG_LEVEL の値検証（有効な値のみ許容）。

- ニュース NLP / AI 統合 (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを ai_scores テーブルへ書き込み。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を提供する calc_news_window。
    - バッチサイズ、1銘柄あたり最大記事数/文字数、JSON Mode の使用、レスポンス検証、スコア ±1.0 のクリップ等を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。失敗時は部分スキップして継続（フェイルセーフ）。
    - DuckDB の executemany 空リスト制約に対応した安全な DELETE → INSERT ロジック（部分失敗時に既存スコアを保護）。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事の抽出にマクロキーワード群を利用、OpenAI を用いたマクロセンチメント評価（JSON 出力期待）。
    - API リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）、スコアの クリップ、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。prices_daily クエリは target_date 未満のデータのみ参照。

  - OpenAI 呼び出しはテスト容易性を考慮し内部でラップ（_call_openai_api）しており、tests から差し替え可能。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX カレンダー（market_calendar）に基づく営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB がまばらな場合の曜日ベースフォールバック、最大探索日数制限、NULL 値検出時の警告など堅牢性を考慮。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新するジョブ。バックフィル（直近数日再フェッチ）と健全性チェックを実装。

  - pipeline / ETL:
    - ETLResult データクラスの実装と public re-export（kabusys.data.etl）。
    - 差分更新戦略、backfill、品質チェック呼び出し用の土台を提供。
    - DuckDB の最大日付取得やテーブル存在チェックなどのユーティリティ関数を実装。

- リサーチ機能 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）を計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - DuckDB ベースの SQL を主体とした実装、データ不足時の None 戻し、結果は (date, code) をキーとする dict のリストで返却。

  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、検証用制約あり）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関）。
    - ランク関数 rank（同順位は平均ランク）、統計サマリー関数 factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等の外部ライブラリに依存しない純 Python 実装。

- DuckDB 周辺の互換性と堅牢化
  - DuckDB の挙動（空の executemany バインド不可等）を考慮した実装。
  - 日付値変換ユーティリティ（_to_date）やテーブル存在チェックを提供。

- ロギングとエラーハンドリング
  - 各モジュールで詳細なログメッセージを出力（INFO/WARNING/DEBUG）。
  - DB 書き込みではトランザクション（BEGIN/COMMIT/ROLLBACK）を使用し、ROLLBACK 失敗時も警告ログを出す実装。

Security
- OpenAI API キーやその他機密情報は環境変数経由での注入を想定。自動 .env ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes
- OpenAI の応答は JSON モードでの利用を想定しており、レスポンスのパースや検証に厳しめのロジックを採用しています。外部 API の仕様変更により動作が変わる可能性があります。
- 現バージョンでは PBR や配当利回りなど一部バリューファクターは未実装（calc_value に注記あり）。

Acknowledgements
- 本リリースは DuckDB と OpenAI SDK を利用する設計を中心に、データ収集・品質管理・AI スコアリング・研究分析機能をワンパッケージで提供することを目的としています。各機能は単体でテスト可能な構造（外部 API キー注入、内部呼び出しの差し替えポイント等）で実装されています。