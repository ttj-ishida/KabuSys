CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従っています。  

[0.1.0] - 2026-03-29
--------------------

Added
- 初回リリース。kabusys パッケージの基本機能群を追加。
  - パッケージメタ:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - 環境設定:
    - .env / 環境変数読み込みユーティリティを実装（src/kabusys/config.py）。
      - プロジェクトルートを .git または pyproject.toml から検出して自動で .env/.env.local を読み込む（自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
      - .env の行パーサは export KEY=val 形式やシングル/ダブルクォート、エスケープ、インラインコメントを考慮して安全にパース。
      - OS 環境変数を保護する protected 上書き制御、override フラグのサポート。
      - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境等をプロパティ経由で取得。環境値検証（KABUSYS_ENV, LOG_LEVEL 等の許容値チェック）を実装。
      - 必須環境変数が未設定の場合は ValueError を送出するユーティリティ _require。
      - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

  - AI 関連:
    - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
      - raw_news と news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出。
      - タイムウィンドウ（JST 前日15:00〜当日08:30）計算ユーティリティ calc_news_window。
      - バッチ処理（1APIコールあたり最大20銘柄）、1銘柄あたりの記事制限（最大記事数/最大文字数）を実装しトークン肥大化に対応。
      - レスポンスを厳密にバリデーションしてスコアを ±1.0 にクリップ。失敗時はフェイルセーフでスキップ。429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
      - テスト容易性のため _call_openai_api を差し替え可能に設計。
      - score_news API を公開（DuckDB 接続、target_date 指定で動作）。
    - 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）
      - ETF 1321（225連動ETF）の200日MA乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を決定。
      - マクロニュースの抽出・LLM 呼び出し（gpt-4o-mini, JSON mode）、リトライ/フォールバック（API失敗時 macro_sentiment=0.0）を実装。
      - lookahead バイアス対策（target_date 未満データのみ使用、datetime.today() を直接参照しない）。
      - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う public API score_regime。

  - Research（定量研究）:
    - ファクター計算モジュール（src/kabusys/research/factor_research.py）
      - Momentum: mom_1m, mom_3m, mom_6m, 200日MA乖離（ma200_dev）。
      - Volatility/Liquidity: 20日 ATR（atr_20）、相対ATR、20日平均売買代金、出来高比率等。
      - Value: PER（EPSが0/欠損時は None）、ROE（raw_financials からの取得）。
      - DuckDB 上の SQL とウィンドウ関数を活用した効率的実装。データ不足時の None ハンドリング。
    - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
      - 将来リターン計算 calc_forward_returns（任意ホライズン、horizons 検証あり）。
      - IC（Spearman ρ）計算 calc_ic（ランク付け・欠損排除・最小サンプル数チェック）。
      - ランク変換ユーティリティ rank（同順位は平均ランク、丸め誤差対策あり）。
      - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
    - research パッケージ __init__ にて主要関数を再エクスポート。

  - Data（データ基盤）:
    - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
      - market_calendar テーブルの存在有無に応じた営業日判定ロジック。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days 等のユーティリティ。DB 登録がない場合は曜日ベース（週末除外）でフォールバック。
      - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等保存。バックフィル・健全性チェックを実装。
      - 最大探索日数やルックアヘッド等の安全措置を実装して無限ループや異常データを回避。
    - ETL パイプライン（src/kabusys/data/pipeline.py）
      - ETLResult データクラス（結果集約、品質問題とエラーの収集、辞書への変換）を実装。
      - 差分取得／バックフィル／品質チェック（quality モジュール利用）の設計方針を具現化。
      - 内部ユーティリティ（テーブル存在チェック、最大日付取得、トレーディング日補正等）を提供。
    - etl モジュールは pipeline.ETLResult を再エクスポート（src/kabusys/data/etl.py）。
    - jquants_client と quality モジュールと連携する設計（外部保存/取得処理は jquants_client 経由）。

  - パッケージ初期化/エクスポート:
    - ai、research パッケージの __init__ で主な API をエクスポート。
    - ルート __init__ で __all__ に data, strategy, execution, monitoring を定義（strategy 等は今後の追加想定）。

Security
- OpenAI API キー等の秘密情報は環境変数経由で取得する設計。Settings._require により必須変数の不在を明示的に検出する。

Notes / ユーザ向け補足
- 必須環境変数（主なもの）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を使う機能を利用する場合は OPENAI_API_KEY が必要（score_news, score_regime 等）。
- デフォルトの DB ファイルパスは settings で指定可能（DUCKDB_PATH, SQLITE_PATH）。
- 自動的な .env ロードは開発時に便利だが、CI/テストで干渉する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DuckDB の executemany に空リストを渡せない制約（0.10系）に対する防御実装が含まれます（ETL / ai のテーブル書き込み処理）。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。