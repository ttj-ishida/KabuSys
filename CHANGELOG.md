CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
バージョンごとに「Added / Changed / Fixed / Deprecated / Removed / Security」のカテゴリを用いています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-31
------------------

Added
- 初回公開: KabuSys 日本株自動売買システムの基礎モジュール群を追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py: __version__ = "0.1.0"、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
  - 設定・環境変数管理
    - src/kabusys/config.py:
      - .env/.env.local を自動ロードする仕組みを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
      - .env パーサを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
      - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベルの取得とバリデーションを実装。
      - 環境変数未設定時の例外報告（_require）を実装。
  - AI（自然言語処理）機能
    - src/kabusys/ai/news_nlp.py:
      - raw_news を対象に OpenAI（gpt-4o-mini）を用いたバッチセンチメント解析を実装。
      - JST 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を提供（calc_news_window）。
      - 銘柄ごとに記事を集約し（最大記事数・文字数トリム）、最大 20 銘柄/チャンクで API に送信。
      - JSON Mode 応答の検証ロジック（validate・型チェック・スコアクリップ）を実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。失敗時はフェイルセーフでスキップ（例外は上位へ投げない）。
      - DuckDB への idempotent な書き込み（DELETE → INSERT）を実装し、部分失敗時に既存データを保護する設計。
      - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
      - 公開関数: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
    - src/kabusys/ai/regime_detector.py:
      - ETF 1321（Nikkei225 連動 ETF）の 200 日移動平均乖離（重み 70%）とニュース由来の LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
      - LLM 呼び出しは独立実装でモジュール結合を避ける設計（news_nlp の private を共有しない）。
      - API リトライ・エラーハンドリング、API 失敗時の macro_sentiment=0.0 フェイルセーフを実装。
      - 判定結果を market_regime テーブルへ冪等的（BEGIN / DELETE / INSERT / COMMIT）に保存。
      - 公開関数: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。
  - Data / ETL / カレンダー関連
    - src/kabusys/data/calendar_management.py:
      - JPX カレンダー管理（market_calendar）の取得/保存ロジックと営業日判定ユーティリティを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar が未取得の場合には曜日ベース（土日休み）でフォールバックする一貫した挙動を実装。
      - calendar_update_job による J-Quants からの差分取得・バックフィル（直近 N 日再フェッチ）・健全性チェックを実装。
    - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py:
      - ETL パイプラインの骨格を実装。差分取得、idempotent 保存、品質チェック（quality モジュールとの連携）方針を反映。
      - ETLResult dataclass を公開して ETL 実行結果（取得数・保存数・quality issues・errors）を集約可能に。
      - _get_max_date / _table_exists 等の DB ユーティリティを実装。
    - src/kabusys/data/__init__.py:
      - pipeline.ETLResult を再エクスポート（data.etl）。
  - Research（因子・特徴量探索）
    - src/kabusys/research/factor_research.py:
      - Momentum / Volatility / Value 等の定量ファクター計算を実装（calc_momentum, calc_volatility, calc_value）。
      - DuckDB SQL を活用し prices_daily/raw_financials を参照して計算。結果は dict のリストで返却。
      - MA200 や ATR 等の欠損処理（データ不足時に None を返す）を実装。
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
      - pandas 等に依存しない純粋標準ライブラリ実装、null/非有限値除外などの堅牢な処理。
    - src/kabusys/research/__init__.py:
      - 主要関数を __all__ で公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - 小さなユーティリティ / 初期化
    - src/kabusys/ai/__init__.py: score_news を公開。
    - 主要設計方針として「datetime.today()/date.today() を参照しない（ルックアヘッドバイアス防止）」が各 AI / research モジュールで明示的に守られている。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照する設計。キー管理は呼び出し側で行うことを想定。

Notes / 備考
- DuckDB を主な分析 DB として想定しており、executemany の空リストバインド等の実装上の互換性考慮（DuckDB 0.10 の制約）に配慮している箇所がある（ai/news_nlp.py, data/pipeline.py）。
- OpenAI 呼び出しは gpt-4o-mini と JSON mode を想定しており、レスポンスパースや冗長テキストに対する復元処理が実装されている。
- ロギングは各モジュールに導入されており、警告や例外時の情報がログに残る設計。

今後の予定（想定）
- strategy / execution / monitoring 周りの具体的実装・テスト充実化。
- jquants_client 周辺の外部 API クライアント実装および単体テスト強化。
- CI での DB モック・OpenAI モックを使ったエンドツーエンドテスト整備。

--- 
（本 CHANGELOG はコードベースの実装内容から推測して記載しています。実際のコミット履歴・リリースノートがある場合はそれに合わせて内容を調整してください。）