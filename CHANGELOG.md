CHANGELOG
=========

すべての重要な変更はここに記録します。本ファイルは Keep a Changelog の形式に準拠します。

Unreleased
----------

（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-04
-----------------

Added
- 初回リリース。kabusys パッケージを公開。
- 環境設定管理モジュールを追加（kabusys.config）
  - .env および .env.local をプロジェクトルートから自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - export KEY=val 形式やクォート、インラインコメント等に対応した行パーサ実装。
  - 上書きポリシー（override / protected）をサポートし、OS 環境変数の保護を実装。
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB / 監視 / ログ設定等のプロパティを型付きで取得。環境値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。
- AI 関連モジュールを追加（kabusys.ai）
  - news_nlp.score_news: raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価、ai_scores テーブルへ書き込み。
    - バッチ送信（最大 20 銘柄）/記事・文字数トリム/JSON Mode を利用した堅牢なレスポンス検証。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフの実装。部分失敗時にも既存スコアを保護するための delete→insert ロジック。
    - テスト容易性のため OpenAI 呼び出し部を差し替え可能（_call_openai_api を patch）。
    - ニュース収集ウィンドウの計算（JST 基準）を提供する calc_news_window。
  - regime_detector.score_regime: ETF 1321 の 200 日 MA 乖離とニュース由来のマクロセンチメントを合成し、market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出、OpenAI による JSON 応答のパース、リトライ／フォールバック（失敗時 macro_sentiment=0.0）。
    - ルックアヘッドバイアス防止（target_date 未満のデータのみ使用）。
- Data / ETL / カレンダー関連モジュールを追加（kabusys.data）
  - pipeline.ETLResult を提供（ETL 実行結果を構造化して返す dataclass）。
  - calendar_management: JPX カレンダー管理ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が存在しない場合は曜日ベースのフォールバックを使用。
    - 夜間バッチ calendar_update_job で J-Quants から差分取得し冪等保存（バックフィル・健全性チェックを実装）。
  - pipeline / etl: ETL 処理方針とユーティリティを実装（差分取得、保存、品質チェック連携の設計）。
- Research モジュールを追加（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）。
    - Momentum（1M/3M/6M）、MA200 乖離、ATR、流動性指標、PER/ROE 計算等を実装。
    - データ不足時は None を返すなど堅牢な挙動。
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（外部ライブラリに依存せず実装）。
    - 将来リターン計算（データがない場合は None）、IC（Spearman のランク相関）、統計サマリー等。
- その他
  - パッケージ初期化（__version__ = "0.1.0"、公開サブパッケージ一覧）。

Changed
- （初回リリースのため既存バージョンからの "変更" はありません）

Fixed
- （初回リリースのため既存バグ修正履歴はありませんが、実装として多くの堅牢化対策を盛り込んでいます）
  - OpenAI API 呼び出し周りでの各種エラー（429 / 接続断 / タイムアウト / 5xx）へのリトライとフォールバック実装。
  - DuckDB の executemany に対する互換性問題を考慮し、空パラメータでの呼び出しを回避するガードを導入。
  - JSON モードでも前後余計なテキストが混入する想定のもと、最外側の {} を抽出して復元するパース耐性を実装。
  - lookahead（ルックアヘッド）バイアスを防ぐため date 比較を厳格化（target_date 未満／排他条件）。

Security
- 環境変数の取り扱いに配慮。自動読み込み時に OS 環境変数を保護する protected キーセットを導入。

Notes / 実装上の重要な設計判断
- ルックアヘッドバイアス防止:
  - 全ての「日次算出」API（ニュース集約・ファクター算出・レジーム判定等）は datetime.today()/date.today() を直接参照しない設計。呼び出し側が target_date を与えることで過去データのみを使用。
- DB 書き込みは冪等性を重視:
  - market_regime / ai_scores 等は DELETE → INSERT あるいは ON CONFLICT ロジックで既存データを上書きし、部分失敗時に他レコードを破壊しない設計。
- OpenAI 連携:
  - gpt-4o-mini の JSON Mode を利用し、厳密な JSON 出力を期待するプロンプト設計。
  - API レスポンスの不備や例外発生時はスコアを 0 にフォールバックするなどフェイルセーフを優先。
- テスト容易性:
  - _call_openai_api を patch 可能にしてユニットテストで外部依存を切り離せるようにしている。
- DuckDB 互換性:
  - executemany に空リストを渡さない、list バインドの不安定さを回避する等、DuckDB 実装差異への実用的配慮を行っている。

開発者向けヒント
- 自動 .env ロードはプロジェクトルート探索に __file__ を使用するため、CWD に依存せずパッケージ配布後も動作します。テストで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API キーは api_key 引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照します。
- news_nlp のタイムウィンドウは JST 基準（前日 15:00 ～ 当日 08:30 JST）で、内部的には UTC naive datetime に変換して DB と比較します。

今後の予定（未実装 / TODO）
- PBR・配当利回りなどバリュー指標の拡張（current: PER・ROE のみ実装）。
- ETL のより詳細な品質チェック結果に基づく自動アクション（現在は問題を収集して呼び出し元に委ねる）。
- モデルやプロンプトのチューニング、より堅牢な JSON 検証ロジックの追加。

--- 

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース差分に基づいて更新してください。）