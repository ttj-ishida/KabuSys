# CHANGELOG

すべての重要な変更は「Keep a Changelog」の慣例に従って記録します。  
このファイルはコードベースから推測して作成したリリース履歴です。

なお、パッケージのバージョンは src/kabusys/__init__.py の __version__ に準拠しています。

## [Unreleased]

（現在差分はありません。次回リリースに向けてここに変更点を記載してください）

---

## [0.1.0] - 2026-03-27

初期リリース。日本株自動売買・データ基盤・リサーチ・NLP/LLM評価を含む基本機能を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0, __all__ 指定）。
  - サブパッケージ構成の公開: data, strategy, execution, monitoring（外部参照用のエントリポイント）。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env および .env.local をプロジェクトルートから自動読み込み (優先度: OS 環境 > .env.local > .env)。
  - .env パーサ実装（export KEY= 値形式、シングル/ダブルクォート、エスケープ、インラインコメントルール対応）。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスにより主要設定をプロパティで提供（J-Quants、kabuステーション、Slack、DB パス、実行環境、ログレベル等）。
  - 環境変数の必須チェック（_require）と値検証（KABUSYS_ENV, LOG_LEVEL の検証）。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/コール）、記事数・文字数トリム、JSON Mode による厳密なレスポンス期待。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）、レスポンス検証とスコアの ±1.0 クリップ。
    - DB への書き込みは部分失敗を考慮し、対象コードのみ DELETE → INSERT で置換（冪等性確保）。
    - テスト容易性: _call_openai_api の差し替えが可能。

  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
    - ma200_ratio の算出（target_date 未満データのみ利用、ルックアヘッド防止）、マクロ記事抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - テスト容易性: _call_openai_api の差し替えが可能。

- データ基盤（Data） (src/kabusys/data/)
  - カレンダー管理 (calendar_management.py)
    - market_calendar を参照する営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 未取得時は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants から JPX カレンダーを差分取得・バックフィル・保存（冪等、健全性チェックあり）。
    - 最大探索日数やバックフィル/先読み日数などの安全パラメータを導入。

  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスにより ETL 実行結果・品質問題・エラー集約を提供。
    - 差分更新ロジック（最終取得日から未取得日を自動算出、backfill による再取得）と idempotent 保存を想定（jquants_client 依存）。
    - 品質チェックモジュール（quality）と連携し、問題を収集して呼び出し側が判断できる設計（Fail-Fast ではない）。
    - 複数の DB 存在チェック／最大日付取得ユーティリティを実装。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER、ROE）などのファクター計算関数を実装。
    - DuckDB SQL を用いた効率的なウィンドウ集計、データ不足時の None 処理。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank・factor_summary 等の統計ユーティリティを実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で完結する設計。
  - research パッケージは主要関数を __all__ で公開（zscore_normalize は別モジュールに依存）。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 削除 (Removed)
- （初期リリースのため該当なし）

### 非推奨 (Deprecated)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーの取り扱いは引数注入または環境変数 OPENAI_API_KEY を使用。APIキー未設定時は明示的に ValueError を送出しているため、不意のロギングなどで漏洩しない運用を想定。

---

注記:
- LLM 呼び出し関連は gpt-4o-mini と JSON Mode を前提に設計されており、レスポンスパース失敗や API 障害に対してフェイルセーフ（中立スコアやスキップ）を採用しています。
- ルックアヘッドバイアス防止のため、いずれのモジュールも日付計算で datetime.today()/date.today() を直接参照しない、target_date を明示的に受け取る設計になっています。
- 実際のリリースノートでは jquants_client の実装状況や strategy/execution/monitoring の具体的な機能追加（未提供ファイルの有無）に応じて追記してください。