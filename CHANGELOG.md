CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
このプロジェクトは "Keep a Changelog" の形式に従います。

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, Removed, Security 等）に分けて記載しています。
- バージョン 0.1.0 は初回リリース（初期実装）として記載しています。

[Unreleased]
------------

（無し）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期公開: kabusys (バージョン 0.1.0)
  - パッケージのエントリポイントと公開モジュールを定義 (src/kabusys/__init__.py)。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルートから自動読み込みする仕組みを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み優先順は OS 環境変数 > .env.local > .env。
    - OS 側の環境変数キーを保護する protected 機能を導入（既存の OS 環境変数を上書きしない）。
  - 柔軟な .env パーサを実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォートとバックスラッシュエスケープ処理を考慮。
    - インラインコメントの扱い（クォート外で直前がスペース/タブならコメント判定）。
  - Settings クラスを提供し、環境変数から安全に設定値を取得:
    - J-Quants / kabu API / Slack / DB パス / システム設定（env, log_level）等のプロパティを実装。
    - env と log_level の値検証（許容値の列挙）を実装。
    - DuckDB / SQLite のパスはデフォルト値を持ち Path 型で返す。

- AI 関連機能 (src/kabusys/ai/)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）を用いてセンチメントを計算。
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30）を calc_news_window で実装。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・記事トリム（_MAX_CHARS_PER_STOCK 等）を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳格なバリデーションとスコアのクリップ（±1.0）を実装。
    - DuckDB の executemany の空リスト制約に対応する実装（空時の実行回避）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
    - 結果を ai_scores テーブルへ冪等的に書き込む（対象コードのみ DELETE → INSERT）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と
      マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジームを判定。
    - prices_daily / raw_news を参照し、OpenAI を呼び出して macro_sentiment を算出。
    - API エラーやパースエラー時はフェイルセーフで macro_sentiment=0.0 として継続。
    - レジームスコアの計算と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
  - ai パッケージ __all__ に score_news（news_nlp）を公開。

- データ基盤機能 (src/kabusys/data/)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を休日）を使用。
    - DB 登録ありの場合は DB 値を優先し、未登録日は曜日フォールバックで一貫した挙動を提供。
    - next/prev_trading_day の最大探索日数制限（_MAX_SEARCH_DAYS）を実装して無限ループを防止。
    - calendar_update_job を実装し、J-Quants API から差分取得〜market_calendar テーブルへ冪等的保存を行う（バックフィル・健全性チェックあり）。
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを導入（ETL 実行結果の集約、品質問題やエラーの収集を含む）。
    - 差分取得、保存（jquants_client を用いた Idempotent 保存）、品質チェックを行う ETL の設計方針を実装（関数群は部分実装含む）。
    - etl モジュールで ETLResult を再エクスポート。
  - jquants_client を想定した fetch/save の呼び出し設計（詳細実装は依存モジュール側）。

- リサーチ機能 (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: mom_1m / mom_3m / mom_6m, ma200_dev（200 日移動平均乖離率）を計算する calc_momentum を実装。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算する calc_volatility を実装。
    - Value: raw_financials から EPS/ROE を取得して PER / ROE を計算する calc_value を実装。
    - DuckDB を用いた SQL ベースの計算。データ不足時は None を返す設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（horizons 対応、入力検証あり）。
    - IC（Spearman のランク相関）を計算する calc_ic（None/データ不足処理あり）。
    - rank ユーティリティ（同順位の平均ランク処理、丸めで ties を扱う）。
    - factor_summary（count/mean/std/min/max/median の統計サマリー）を実装。
  - research パッケージ __all__ に主要関数を公開し、data.stats.zscore_normalize を再エクスポート。

- 汎用設計・実装上の配慮
  - ルックアヘッドバイアス対策: datetime.today() / date.today() を主要ロジックで参照しない（target_date を外部から注入）。
  - DuckDB の実装差異（executemany の空リスト制約など）に対応した安全実装。
  - API 呼び出しのリトライとログ出力を充実させ、致命的な例外をなるべく抑えて継続できるフェイルセーフ設計。
  - テスト容易性を考慮した差し替えポイント（_call_openai_api のパッチ等）を提供。

Changed
- （初回リリースのため該当無し）

Fixed
- （初回リリースのため該当無し）

Security
- 環境変数読み込み時に OS 環境変数を上書きしない既定振る舞いを採用し、.env ロード時に保護対象キーを扱う設計を導入。
- Settings で必須項目が未設定の場合は ValueError を投げて早期検出。

Notes / Implementation details
- OpenAI クライアントは OpenAI(api_key=...) を想定。レスポンスは JSON Mode を利用し厳密 JSON を期待するが、パーサは余計な前後テキストに対しても復元ロジックを持つ。
- 一部の外部依存（jquants_client、quality モジュール、DB テーブルスキーマ等）は別モジュール実装が前提。
- ログ出力や警告は詳細に加えられており、運用時のデバッグ／監査に役立つ情報を記録する。

問い合わせ
- 追加の変更点やリリースノートの補足が必要であれば、どのモジュールのどの部分を詳細に書くかを指定してください。