CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従います。  
このファイルでは互換性のない変更は Breaking Changes として明示します。

Unreleased
----------

- なし

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初版リリース: kabusys 0.1.0
  - 概要: 日本株自動売買・データプラットフォーム向けのユーティリティ群を提供するライブラリの初期実装。

- コア構成
  - src/kabusys/__init__.py
    - パッケージ公開バージョンを __version__ = "0.1.0" として定義。
    - パブリック API: data, strategy, execution, monitoring を __all__ に設定。

- 設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を読み込む。OS 環境変数は protected として上書き防止。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - 環境変数パースは export 文・クォート・エスケープ・インラインコメントを考慮した実装。
    - 必須設定取得時に未設定なら ValueError を送出する _require を提供。
    - Settings で J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）/環境（development/paper_trading/live）/ログレベル等をプロパティとして公開。

- AI（自然言語処理）関連
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとにセンチメントスコア化し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）計算、記事集約（銘柄ごと最大記事数・文字数トリム）、バッチ送信（最大20銘柄/回）をサポート。
    - レート制限（429）やネットワーク断、タイムアウト、5xx に対する指数バックオフリトライを実装。
    - レスポンス検証ロジック（JSON 抽出、results フィールド、コード照合、スコア数値性のチェック）を搭載。スコアは ±1.0 にクリップ。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_unittest.mock.patch 用フック）。
    - score_news(conn, target_date, api_key=None) を公開（戻り値: 書き込んだ銘柄数）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（'bull' / 'neutral' / 'bear'）を日次判定する機能を実装。
    - news_nlp の calc_news_window を利用してニュースウィンドウを決定、raw_news からマクロキーワードフィルタで記事を抽出し OpenAI により macro_sentiment を取得。
    - OpenAI 呼び出しは独立実装で、リトライ/エラーハンドリングを行い、失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - 判定結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - score_regime(conn, target_date, api_key=None) を公開（戻り値: 1 ＝ 成功）。

- データ / ETL
  - src/kabusys/data/pipeline.py
    - ETL の高レベル設計に基づく ETLResult dataclass を実装（取得件数、保存件数、品質チェック結果、エラー一覧などを格納）。
    - 差分更新や backfill の概念、品質チェックの扱い方（重大度に基づく判定）をコード上で表現。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）および営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった API を提供。
    - DB にカレンダーデータがない場合は曜日ベース（土日休み）でフォールバックする挙動。
    - calendar_update_job: J-Quants からカレンダーを差分取得し保存するバッチ処理（バックフィル、健全性チェックあり）。

  - jquants_client 連携想定（コード内で import 参照。fetch/save 関数呼び出しにより外部 API 結果の保存を想定）。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - ファクター計算群を実装（Momentum / Value / Volatility / Liquidity に対応）。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None、営業日ベースのラグ）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算（EPS=0 や欠損時は None）。
    - すべて DuckDB 上で SQL を利用して計算し、結果を list[dict] で返す設計。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定基準日から将来リターン（任意の営業日ホライズン）を計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（Information Coefficient）を計算。十分なサンプルがない場合は None を返す。
    - rank: 同順位は平均ランクで扱うランク化関数を実装（丸め処理で ties の誤検出を抑制）。
    - factor_summary: count / mean / std / min / max / median を計算する統計サマリー関数を実装。

- 公開再エクスポート
  - src/kabusys/ai/__init__.py で score_news を公開。
  - src/kabusys/research/__init__.py で主要な研究ユーティリティを公開。
  - src/kabusys/data/__init__.py は内部モジュールの公開ポイントとして存在（詳細はモジュール内参照）。

Design / Implementation Notes（設計上の重要点）
- ルックアヘッドバイアス防止:
  - 複数モジュール（news_nlp, regime_detector, research）で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計を採用。
- DB 書き込みは冪等性を考慮:
  - market_regime / ai_scores / calendar 等への保存は既存行削除→挿入、または ON CONFLICT を意識した処理を行う。
- OpenAI API 呼び出し:
  - gpt-4o-mini の JSON モードを利用。429 / ネットワーク / タイムアウト / 5xx に対してリトライ＋バックオフ（指数）を実装。致命的な API 例外はログに落としてフェイルセーフで継続する箇所が多い。
  - テストのために _call_openai_api を差し替え可能に設計。
- DuckDB を主要な分析ストアとして利用。SQL と Python を組み合わせて処理を実装。
- ログ出力を多用し、異常時は警告 / 例外ログを記録。

Breaking Changes
- なし（初回リリース）

Notes / Known limitations
- 外部クライアント実装（jquants_client 等）は別モジュール/外部実装に依存するため、本リポジトリ単体では API 呼び出し部分の動作に別設定・実装が必要。
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で提供する必要がある。未設定時は ValueError を送出。
- DuckDB のバージョン依存の注意点（executemany に空リストを渡せない等）をコード内で回避している。

今後の予定（例）
- strategy / execution / monitoring の具体実装の追加（現状はパッケージ公開のみ）。
- テストカバレッジ拡充、CI 設定、ドキュメント追加（API 使用例、DB スキーマ説明など）。
- OpenAI レスポンスの堅牢性向上（プロンプト改良、応答形式のさらなる検証など）。

-----