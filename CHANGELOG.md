CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従い、重要度は SemVer を想定しています。

Unreleased
----------

- 予定 / 検討中
  - OpenAI 呼び出しの抽象化・モック用インターフェース強化（テスト容易性向上）
  - ETL の差分取得ロジックに対する細かなパラメータ調整（バックフィル日数等）の公開設定化
  - ai モジュールのスコアリング品質向上（プロンプト改善・出力バリデーション強化）
  - DuckDB スキーマ初期化ユーティリティの追加（テスト用 DB 作成補助）

0.1.0 - 2026-03-31
-----------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - src/kabusys/__init__.py にてバージョンと公開モジュールを定義。
  - 公開モジュール: data, strategy, execution, monitoring（将来的な拡張を想定した名前空間を確立）。

- 環境設定/ロード機能
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）。
    - export KEY=val 形式やクォート／エスケープ、行コメント等に対する堅牢なパーサーを実装。
    - 既存 OS 環境変数を保護する protected パラメータの概念を導入。
    - 必須環境変数取得用 _require と Settings クラスを提供。主要設定:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - DUCKDB_PATH / SQLITE_PATH（デフォルトパス）
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - Settings インスタンスを settings として公開。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチサイズ、記事数・文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - JSON Mode 応答のバリデーション機能を実装し、結果のクリップ（±1.0）と ai_scores テーブルへの冪等書き込み（DELETE → INSERT）を行う。
    - テスト容易性のため OpenAI 呼び出し関数を内部で分離（_call_openai_api をパッチ可能）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみ使用しルックアヘッドを防止。
    - マクロニュース抽出はマクロキーワード群を定義し raw_news から取得。
    - OpenAI 呼び出しは独立実装、API エラー時は macro_sentiment=0.0 のフォールバックで継続。
    - 結果を market_regime テーブルへ冪等に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
    - リトライ・エラー処理・ログ出力を備える。

- データ関連モジュール
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを行い、マップに依存しつつ一貫性を確保。
    - calendar_update_job により J-Quants API から差分取得・バックフィル・保存（jq.fetch_market_calendar / jq.save_market_calendar を使用）を実行。
    - 健全性チェック（未来日閾値）や最大探索日数制限を実装。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの基本を実装。差分取得・保存・品質チェックのフローを想定。
    - ETLResult dataclass を導入し取得件数・保存件数・品質問題・エラーの集約を実装。
    - DuckDB テーブルの最大日付取得、テーブル存在判定ユーティリティ等を提供。
    - src/kabusys/data/etl.py で ETLResult を公開再エクスポート。

  - src/kabusys/data/__init__.py
    - data 名前空間を準備（中核モジュール群の集合）。

- リサーチ / ファクター関連
  - src/kabusys/research/factor_research.py
    - モメンタム（1/3/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、バリュー（PER, ROE）などの定量ファクター計算関数を実装:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB 上で SQL を用いて計算し、(date, code) をキーとする dict のリストで返す設計。
    - データ不足時の取り扱いや None の返却方針を明確化。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計要約（factor_summary）を実装。
    - pandas など外部依存を避け、標準ライブラリと DuckDB のみで実装。
    - スピアマンランク相関の実装、ties の平均ランク処理を含む。

  - src/kabusys/research/__init__.py にて主要関数をエクスポート（zscore_normalize は kabusys.data.stats から）。

Changed
- 設計方針の明示
  - 多くのモジュールで「datetime.today()/date.today() を参照しない」方針を採用し、ルックアヘッドバイアスを回避する実装になっていることを README/ドキュメントに反映する前提で設計を統一。

Fixed
- 初期実装段階でのフォールバック・フェイルセーフを複数箇所で提供
  - OpenAI API 呼び出しの失敗時に例外を直接放さずフォールバック（0.0）で継続する箇所を明確化（news_nlp, regime_detector）。
  - DuckDB executemany の空パラメータへの互換性に対応するガードを実装（空リストでは実行しない）。

Notes / Known limitations
- OpenAI への依存
  - AI スコアリングは OpenAI（gpt-4o-mini）を使用する設計。実行には OPENAI_API_KEY（または api_key 引数）の設定が必須。
  - API コールは外部サービス依存のためレート制限や料金が発生する点に注意。

- DB スキーマ
  - 本コードは prices_daily / raw_news / news_symbols / ai_scores / market_regime / raw_financials / market_calendar などの DuckDB テーブルを前提としている。初期化スクリプトは含まれていないため、運用前にスキーマ準備が必要。

- テスト設計
  - OpenAI 呼び出し関連関数はパッチ可能な形で分離している（ユニットテストでのモックが容易）。ただし実運用でのエッジケース検証は追加の統合テストが望ましい。

開発者向けメモ
- 環境ロードはプロジェクトルート特定に __file__ を基準とするため、パッケージ配布後も cwd に依存しない動作を行う。
- settings オブジェクトをインポートすることでアプリケーション構成値へ容易にアクセス可能。
- 多くのDB操作は冪等性を意識して実装（DELETE → INSERT、ON CONFLICT を期待する save 関数利用など）。

Copyright
- 本リリースは初期実装の記録です。今後のパッチ・機能追加に合わせて CHANGELOG を更新してください。