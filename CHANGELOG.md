Changelog
=========

すべての注目すべき変更はこのファイルに記録します。This project adheres to "Keep a Changelog".
リリースはセマンティックバージョニングに従います。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-31
-------------------

追加 (Added)
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
    - パッケージ公開インターフェースとして data, strategy, execution, monitoring をエクスポート。
- 設定・環境変数管理モジュール (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - 読込優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export 形式、クォート・エスケープ、インラインコメント等に対応。
  - Settings クラスで主要設定をプロパティとして公開（J-Quants / kabu API / Slack / DB パス / 環境フラグ等）。バリデーション（許容される env 値・ログレベル）を実装。
- AI モジュール (`kabusys.ai`)
  - ニュースセンチメントスコアリング (`news_nlp.py`)
    - raw_news / news_symbols を読み取り、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み。
    - バッチサイズ、トリム長、リトライ（指数バックオフ）等の制御を実装。
    - レスポンスのバリデーションと数値クリッピング（±1.0）。
    - DuckDB 互換性のため executemany 前に空パラメータチェックを行う等の実運用考慮を反映。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（関数単位で patch 可能）。
  - 市場レジーム判定 (`regime_detector.py`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を算出。
    - OpenAI 呼び出し（gpt-4o-mini）への堅牢なリトライ/エラー処理を実装。API 失敗時は macro_sentiment = 0.0 で継続（フェイルセーフ）。
    - 計算結果は DuckDB の market_regime テーブルへ冪等書き込み（トランザクション BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス回避の設計（datetime.today()/date.today() を直接参照しない、prices_daily のクエリは target_date 未満のデータのみ使用）。
- データプラットフォーム関連 (`kabusys.data`)
  - ETL パイプライン (`pipeline.py` / `etl.py`)
    - ETLResult データクラスを公開。ETL の取得件数、保存件数、品質チェック結果、エラー一覧を保持。
    - 差分取得、バックフィル、品質チェック方針を反映した設計（J-Quants API からの差分取得と idempotent 保存を想定）。
    - DuckDB からの最大日付取得、テーブル存在チェック等のユーティリティを実装。
  - マーケットカレンダー管理 (`calendar_management.py`)
    - JPX カレンダー（market_calendar）を夜間に差分で取得して更新する calendar_update_job を実装（バックフィル、健全性チェック付き）。
    - 営業日判定ロジック: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB 登録値優先だが未登録日は曜日ベースでフォールバック。
    - 安全策として検索範囲上限（_MAX_SEARCH_DAYS）や将来日付のサニティチェックを実装。
  - jquants_client と quality モジュールとの連携を想定（pipeline で使用）。
- リサーチ/ファクター関連 (`kabusys.research`)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）等のファクター計算関数を実装。prices_daily / raw_financials を参照。
    - テーブルベースの SQL 処理で DuckDB 上で計算を行い、結果を (date, code) ベースの dict リストで返す。
  - feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）。
    - IC（Information Coefficient）calc_ic（スピアマンランク相関）とランク変換ユーティリティ rank。
    - factor_summary：基本統計量（count/mean/std/min/max/median）を算出。
- DuckDB を一次データ層として広く採用
  - 各処理は DuckDB 接続を受け取り SQL と最小限の Python ロジックで実行される設計。
  - DuckDB のバージョン差（executemany の空リスト制約など）への対策をコードに反映。
- ロギングと堅牢性
  - 各モジュールで詳細なログ出力を実装（info/warning/debug/exception）。
  - API 失敗時のフォールバックやリトライ戦略、トランザクションの ROLLBACK 保護など、実運用を想定した堅牢性を確保。
- テストフレンドリネス
  - OpenAI への実際の呼び出しを関数単位で差し替えられるようにしてユニットテストでモックしやすく設計。

変更 (Changed)
- （初回リリースのため該当なし）

修正 (Fixed)
- （初回リリースのため該当なし）

注意事項 (Notes)
- OpenAI API の利用には OPENAI_API_KEY が必要。news_nlp.score_news / regime_detector.score_regime は api_key 引数でキーを注入可能。
- .env 自動ロードはプロジェクトルートの検出に依存。配布後やテスト時に自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB スキーマ（tables）の有無や列の NULL 値に対するフォールバック挙動が多くの関数で定義されています。実運用導入時はスキーマ準備とデータ品質確認を推奨します。

AUTHORS
- このリリースの主要実装者: (コードから推測)

―――

（この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。）