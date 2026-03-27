# Changelog

すべての重要な変更はこのファイルで記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングに従います。

## [0.1.0] - 2026-03-27

### Added
- 初回リリース。パッケージ名: kabusys、バージョン: 0.1.0。
- パッケージ公開インターフェース:
  - src/kabusys/__init__.py で data, strategy, execution, monitoring を公開。
- 環境設定管理:
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - export KEY=val 形式、クォート付き値、インラインコメントの取り扱いに対応した堅牢な .env パーサ実装。
    - 既存 OS 環境変数を保護する protected オプション（.env/.env.local 上書き制御）。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを公開。
    - 必須環境変数未設定時には ValueError を送出する _require 実装。
- AI モジュール:
  - src/kabusys/ai/news_nlp.py
    - raw_news + news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/呼び出し）、記事数・文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ、レスポンス検証、スコアクリップ（±1.0）。
    - calc_news_window による JST ベースのニュースウィンドウ計算（前日 15:00 ～ 当日 08:30 JST → UTC に変換）。
    - テスト容易性のため OpenAI 呼び出し点に差し替え可能な内部関数（unittest.mock.patch を想定）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM マクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワード抽出、OpenAI 呼び出し（リトライ・バックオフ・エラーハンドリング）、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 失敗時はマクロセンチメントを 0.0 とするフェイルセーフ。
- データ / ETL:
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass を導入し、取得数・保存数・品質チェック結果・エラーを集約。
    - 差分取得・バックフィル・品質チェックを想定した ETL 設計（J-Quants クライアント経由での保存・idempotent 保存を想定）。
    - DuckDB 固有の挙動（executemany に空リストを渡せない問題）への対応を記述。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を公開インターフェースとして再エクスポート。
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先、未登録日は曜日ベース（週末除外）のフォールバックを実装し、スキャン上限で無限ループ防止。
    - JPX カレンダーを J-Quants から差分取得して更新する夜間バッチ（calendar_update_job）を実装。バックフィル・健全性チェックを搭載。
- Research（リサーチ）モジュール:
  - src/kabusys/research/factor_research.py
    - Momentum, Value, Volatility, Liquidity などの定量ファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
      - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算。
    - DuckDB のウィンドウ関数を活用し営業日ベースのスキャン・データ不足判定を考慮。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意のホライズン、入力検証あり）。
    - calc_ic: スピアマンランク相関（ランク化は同順位平均ランクを採用）。
    - rank, factor_summary 等の統計ユーティリティ（外部ライブラリ不使用で実装）。
  - research パッケージの __init__.py で主要関数群をエクスポート。
- データユーティリティ:
  - DuckDB 接続を前提にしたSQL中心の実装で、外部 API 呼び出しや取引実行には依存しない設計（Research / Data / AI の分離）。
- ロギング:
  - 各モジュールで詳細な logger 出力を実装（INFO/DEBUG/WARNING を適所で出力）。

### Changed
- 設計注記として全てのスコアリング・判定関数は datetime.today()/date.today() を直接参照せず、target_date 引数で明示的に日付を与える方針を採用（ルックアヘッドバイアス回避）。
- OpenAI 呼び出しの実装をニュース系・レジーム系で分け、モジュール間でプライベート関数を共有しないことで疎結合化。

### Fixed
- -（初回リリースのため該当なし）

### Notes / Implementation details
- OpenAI クライアントは openai.OpenAI を利用。JSON Mode（response_format={"type":"json_object"}）を期待するが、パース失敗時の復元処理や部分パースも考慮して堅牢化。
- News/Regime のリトライは 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフを実施。500 未満の API エラーはリトライ対象外でフェイルセーフ。
- ai_scores 書き込みは部分失敗時に他銘柄の既存スコアを保護するため、対象コードのみ削除→挿入の方式を採用。
- DuckDB のバージョン差異（executemany の空リスト不可、リスト型バインドの不安定性等）を考慮した実装になっている。
- 環境変数パーサはシェルライクな形式に対応し、クォート内のエスケープやインラインコメントを適切に扱う実装。

---

今後のリリース案内（予定）
- strategy / execution / monitoring 実装の追加（発注ロジック、実行監視、Slack通知等）。
- 単体テスト・統合テストの追加と CI 設定、型チェック強化。