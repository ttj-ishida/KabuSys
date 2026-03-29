# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。  
リリース履歴はセマンティックバージョニングに従います。

※ 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴ではなく、現時点でパッケージに含まれる主要な機能追加・設計上の注意点をまとめたものです。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-29
初回公開リリース

### Added
- パッケージ基盤
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
  - 各サブパッケージの公開シンボルを __all__ で整理（data, strategy, execution, monitoring）。
- 環境変数 / 設定管理
  - .env ファイルまたは環境変数から設定を読み込む設定モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出する実装（配布後も動作するように __file__ を起点に探索）。
    - .env, .env.local の自動読み込みロジック（OS環境変数優先、.env.local は上書き、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env の行パーサは export プレフィックス・クォートやエスケープ、インラインコメントを考慮した堅牢な実装。
    - 必須設定取得用の _require と Settings クラスを提供。J-Quants / kabu API / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル検証などをサポート。
- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメント解析（score_news）
    - raw_news と news_symbols を集約し、銘柄ごとに前日15:00 JST〜当日08:30 JST の範囲のニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信して ai_scores テーブルへ書き込む処理を実装（src/kabusys/ai/news_nlp.py）。
    - バッチ処理サイズ、記事数・文字数トリム、JSON Mode の利用、レスポンスバリデーション、スコア ±1.0 クリップ、DuckDB 互換性（executemany の空リスト回避）等を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフのリトライや、失敗時のフェイルセーフ（スキップして継続）を実装。
    - テスト用に内部の OpenAI 呼び出しを差し替え可能（unittest.mock.patch 対応）。
    - calc_news_window ユーティリティを公開（UTC naive datetime を返す、JST→UTC の変換ロジック）。
  - 市場レジーム判定（score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して、daily ベースでレジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みする処理を追加（src/kabusys/ai/regime_detector.py）。
    - マクロニュース抽出、LLM 呼び出し（gpt-4o-mini + JSON Mode）、リトライ処理、レスポンスパースのフォールバック、DB トランザクション（BEGIN/DELETE/INSERT/COMMIT）およびロールバック処理を実装。
    - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
- Research（ファクター計算・特徴量探索）
  - factor_research モジュール（src/kabusys/research/factor_research.py）を追加。
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算する calc_momentum。
    - Volatility / Liquidity: 20日 ATR、ATR/価格比、20日平均売買代金、出来高比率を計算する calc_volatility。
    - Value: raw_financials から直近財務を取得し PER / ROE を計算する calc_value（EPS が 0 / 欠損の場合は None）。
    - DuckDB を用いた SQL + Python の実装で、外部 API へはアクセスしない設計。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）を追加。
    - 将来リターン計算（calc_forward_returns: 任意ホライズンで fwd_*d を計算、horizons のバリデーションあり）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）を行う calc_ic。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - 統計サマリー（factor_summary: count/mean/std/min/max/median）。
    - Research パッケージの __init__ で主要機能を再エクスポート。
- Data（データ基盤ユーティリティ）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理（market_calendar テーブル操作、営業日判定、next/prev/get_trading_days、is_sq_day、夜間バッチ calendar_update_job）を実装。
    - DB が空の場合は曜日ベース（平日）でのフォールバックを行う設計。
    - 最大探索日数上限やバックフィル・健全性チェックを実装して無限ループや異常データを防止。
    - jquants_client からのフェッチ・保存を呼び出す処理を持つ（外部 jquants_client を使用）。
  - ETL パイプライン（src/kabusys/data/pipeline.py と etl.py）
    - ETLResult dataclass を実装して ETL の実行結果（取得数・保存数・品質問題・エラー）を構造化。
    - 差分更新・バックフィル・品質チェックのための内部ユーティリティを用意（_get_max_date, _table_exists など）。
    - ETLResult.to_dict により品質問題をタプルから辞書に変換して出力可能。
    - data/etl で ETLResult を再エクスポート。
  - その他
    - data パッケージの骨組みを追加（空の __init__.py を含む）。
- パッケージ公開関係
  - ai, research, data, その他モジュールの __init__ による主要 API の再エクスポートを実装（例: kabusys.ai.score_news, kabusys.research.calc_momentum 等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数で扱う認証情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、OPENAI_API_KEY 等）は必須であり、Settings クラス経由で取得されます。.env/.env.local の取り扱いは注意してください（.env.local は .env を上書き）。
- .env 読み込みはデフォルトで自動実行されますが、テスト等で無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。

### 注意事項 / 設計上のポイント
- ルックアヘッドバイアス防止のため、日付処理は datetime.today()/date.today() を直接参照せず、score_news / score_regime / 各種計算関数は target_date 引数を必須にしている箇所が多くあります。
- OpenAI API 呼び出しは JSON Mode を前提としており、レスポンスのパースに失敗した場合はフェイルセーフとして影響を最小化する設計（スコア 0.0 など）になっています。テスト時には内部呼び出しをモック可能です。
- DuckDB のバージョン差異（executemany の空リスト制約や配列バインドの挙動）を考慮した実装上の工夫が含まれています。
- DB 書き込み時はトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等・安全性を担保するように実装されています。

---

今後のリリース候補（想定）
- バグ修正（レスポンスパースのさらなる堅牢化、DuckDB 互換性の追加対応）
- strategy / execution / monitoring サブパッケージの実装（初期構成では __all__ に名前はあるが実装は未確認）
- テストカバレッジ向上および CI/CD 用の環境設定ドキュメント追加

--- 

（以降のバージョンでは、追加/変更/修正内容を上のフォーマットに従って記載してください。）