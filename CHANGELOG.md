CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に従い、セマンティックバージョニングを用いて記載しています。  
このファイルはコードベースから推測できる実装内容・設計方針に基づいて作成しています。

[Unreleased]
-------------

- 特になし（初回リリースは 0.1.0）

[0.1.0] - 2026-04-04
-------------------

Added
- パッケージ基盤
  - kabusys パッケージ初期リリース。バージョン 0.1.0 を設定。
  - __all__ で主要サブモジュール（data, research, ai, …）を公開。

- 環境設定 / 初期化機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートを .git または pyproject.toml から探索することで、CWD に依存しない自動ロードを実現。
  - .env パーサ：export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などをサポート。
  - .env/.env.local の優先順と上書き制御（protected keys）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
  - 設定取得用 Settings クラスを提供（J-Quants トークン、kabuAPI 設定、LINE API、DB パス、監視設定、システム env/log_level 判定など）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL 等）と便利な is_live / is_paper / is_dev プロパティを実装。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを生成し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを評価。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を実装。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、記事数・文字数トリム、JSON レスポンスのバリデーションとスコアの ±1.0 クリップを実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフを実装。部分成功時に既存スコアを保持するための差し替え（DELETE→INSERT）戦略を採用。
    - DuckDB の executemany の制約（空リスト不可）に配慮した実装。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（内部 _call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を組み合わせ、日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによるニュース抽出、LLM 呼び出し（gpt-4o-mini）、レスポンス JSON パース、スコア合成、クリッピング、しきい値判定を実装。
    - API 障害時は macro_sentiment=0.0 としてフェイルセーフで継続。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と例外発生時の ROLLBACK（失敗時はログ出力）を実装。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の SQL と Python で計算する関数群を実装。
    - データ不足時の None 値処理、ログ出力による診断を整備。
  - feature_exploration
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman のランク相関）実装。
    - ランキング処理（同順位は平均ランク）、統計サマリー（count/mean/std/min/max/median）を標準ライブラリのみで実装。
    - 入力バリデーション（horizons の範囲チェック等）を実装。
  - 研究系ユーティリティ（zscore_normalize 等）を data.stats から再エクスポート。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）を参照する営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、最大探索日数による無限ループ防止を実装。
    - 夜間バッチ更新 job（calendar_update_job）を実装し、J-Quants クライアント経由で差分取得→冪等保存（ON CONFLICT 相当）・バックフィル・健全性チェックを行う。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを実装し、取得数/保存数/品質問題/エラーを集約。
    - 差分更新・backfill・J-Quants クライアント連携・品質チェック（quality モジュール）を想定した設計。品質問題は収集して呼び出し元で判断するモデル（Fail-Fast ではない）。
    - テーブル存在確認・最大日付取得などのユーティリティを実装。

- DB / トランザクション安全性
  - DuckDB を前提としたクエリとトランザクション（BEGIN/COMMIT/ROLLBACK）操作を多用。部分失敗時に既存データを保護するための削除→挿入戦略や executemany の注意事項を盛り込んだ実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし（各モジュールで例外処理やフォールバックを多く実装し、堅牢性を確保）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。API キーの未設定は ValueError で明確に検出する設計。

Notes / 設計ポリシー（概略）
- ルックアヘッドバイアス回避: date.today()/datetime.today() を直接参照せず、target_date を明示的に受け取る関数設計。DB クエリにおいても target_date 未満 / 排他条件を厳格に扱う。
- フェイルセーフ: 外部 API（OpenAI, J-Quants）障害時は例外を無闇に伝播させず、ログ出力の上で安全なデフォルト（0.0 のスコア等）で継続する箇所を設ける。
- テスト容易性: OpenAI 呼び出し等の箇所を差し替えられるよう内部呼び出しを抽象化（patch 可能）している。
- DuckDB 互換性: executemany の挙動やリストバインドの不安定さを考慮した実装を行っている。

Acknowledgements
- 本 CHANGELOG はソースコードの内容および docstring / コメントから推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース時の差分に基づいて補正してください。