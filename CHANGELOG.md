Keep a Changelog 準拠 — CHANGELOG
===============================

フォーマット: https://keepachangelog.com/（日本語）

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-31
--------------------

初回リリース。主要機能群を実装し、ライブラリの公開 API を定義しました。

Added
- パッケージ基礎
  - kabusys パッケージ初期化とバージョン定義を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 設定・環境読み込み
  - .env ファイルおよび環境変数から設定を読み込むユーティリティを実装（src/kabusys/config.py）。
    - プロジェクトルートを .git / pyproject.toml から自動検出して .env/.env.local をロード。
    - export 形式やクォート付き値、インラインコメント処理など堅牢にパース。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数取得ヘルパー _require と Settings クラス（J-Quants / kabu / Slack / DB / ログ設定など）を提供。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
- AI（OpenAI）関連
  - ニュースセンチメントのバッチスコアリングを行う score_news 実装（src/kabusys/ai/news_nlp.py）。
    - gpt-4o-mini を利用、JSON Mode を期待してレスポンスを厳密にバリデーション。
    - チャンク処理（1 API 呼び出しで最大 20 銘柄）、記事トリムやトークン肥大対策（最大記事数・文字数制限）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、部分失敗時の DB 保護（影響範囲の限定）。
    - calc_news_window を含む時刻ウィンドウ計算（JST→UTC 変換、ルックアヘッドバイアス対策）。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
  - マクロニュースと ETF MA を組み合わせて市場レジームを判定する score_regime 実装（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日 MA 乖離（重み 70%）と LLM マクロセンチメント（重み 30%）を合成して regime_score を算出。
    - OpenAI 呼び出しに対するリトライ・フォールバック（API 失敗時は macro_sentiment=0.0）。
    - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
- データ処理（Data Platform）
  - ETL パイプライン結果を表す ETLResult を実装して公開（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
    - ETL の各種カウント、品質チェック結果、エラー集約を保持。辞書変換ユーティリティを提供。
  - JPX カレンダー管理および営業日ユーティリティを実装（src/kabusys/data/calendar_management.py）。
    - market_calendar に基づく is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - J‑Quants からの差分取得を行う calendar_update_job（バックフィル、健全性チェック、ON CONFLICT 相当の保存フローを想定）。
    - カレンダーデータ未取得時の曜日ベースのフォールバックを提供。
- 研究（Research）モジュール
  - ファクター計算（Momentum/Value/Volatility）を実装（src/kabusys/research/factor_research.py）。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の算出。
    - calc_value: raw_financials から EPS/ROE を用いた PER/ROE の算出（最新報告日ベース）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比など。
    - DuckDB SQL とウィンドウ関数を利用して効率的に計算。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）。
    - calc_forward_returns: 指定ホライズンの将来リターン取得（horizons 検証あり）。
    - calc_ic: スピアマンランク相関（情報係数）計算。
    - rank: 同順位の平均ランク処理（浮動小数丸めで ties を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
  - research パッケージの公開インターフェースを提供（src/kabusys/research/__init__.py）。
- データユーティリティ
  - DuckDB を前提とした各種内部ユーティリティ（テーブル存在チェック、日付変換など）を実装。
  - DuckDB の互換性考慮（executemany に空リストを渡さない等）の取り扱いを明記。

Changed
- （初版につき該当なし）

Fixed
- （初版につき該当なし）

Security
- API キーの取り扱い
  - OpenAI API キーは関数引数で注入可能。環境変数 OPENAI_API_KEY を既定の参照先とするが、未設定時は ValueError を送出して誤動作を防止。

Notes / Implementations details（設計上の重要点）
- ルックアヘッドバイアス対策
  - datetime.today() / date.today() を直接参照しない設計（score_news, score_regime 等は target_date を明示的に受け取る）。
  - DB クエリは target_date 未満 / 排他区間を明示して将来データを参照しない。
- フェイルセーフ設計
  - LLM/API 呼び出し失敗時は例外で処理を中断せず、フォールバック値（例: 0.0）で継続する箇所を多数実装。DB 書込失敗時はロールバックして例外を伝播。
- テスト容易性
  - OpenAI 呼び出しを行う内部関数（_kabusys.ai.*._call_openai_api）を簡単にモック可能にしてユニットテストを容易化。
- DuckDB との互換性注意
  - DuckDB のバージョン差異を考慮した実装（executemany の空リスト回避、リスト型バインドの不安定性回避など）。

互換性 / Breaking changes
- 初回リリースのため互換性破壊の履歴はありません。

既知の制限
- OpenAI の JSON Mode に依存しているため、モデル応答の不整合が発生するとスコア算出がスキップされる場合があります（ログに記録）。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、意図的に共有していません（モジュール結合を避けるため）。

今後の予定（例）
- パフォーマンス改善: 大規模データセット向けの並列化 / バッチ最適化。
- 追加ファクター（PBR、配当利回り等）とファクター合成ロジックの拡張。
- モデル切替や非 OpenAI モデルのプラガブル化。

補足
- 各関数・クラスの詳細な使用例・引数仕様はモジュールの docstring を参照してください。