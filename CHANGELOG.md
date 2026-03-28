Keep a Changelog
=================
すべての変更は http://keepachangelog.com/ja/ に準拠して記載しています。
このパッケージはセマンティックバージョニングに従います。

[Unreleased]
------------

### 追加
- 主要なモジュール群の初期実装を追加。
  - パッケージ初期バージョン: 0.1.0

[0.1.0] - 2026-03-28
-------------------

### 追加
- パッケージ基盤
  - kabusys パッケージ初期公開（src/kabusys/__init__.py）。
  - バージョン識別子 __version__ = "0.1.0" を設定。
  - パッケージの公開 API に data, strategy, execution, monitoring を定義。

- 環境設定 & ロード
  - .env ファイルと環境変数を読み込む設定モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出する実装を追加（CWD に依存しない）。
    - .env / .env.local の自動読み込み（優先度: OS環境 > .env.local > .env）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パースの堅牢化:
      - export KEY=val 形式への対応
      - シングル／ダブルクォート、バックスラッシュエスケープ処理
      - インラインコメントの扱い（クォートあり/なしのルール分岐）
    - 環境変数取得ユーティリティ Settings を提供:
      - 必須トークン取得メソッド（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）
      - デフォルト値付き設定（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）
      - KABUSYS_ENV の値検証（development / paper_trading / live）
      - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
      - is_live / is_paper / is_dev のユーティリティプロパティ

- データ基盤（Data）
  - ETL パイプライン基盤を追加（src/kabusys/data/pipeline.py）。
    - 差分更新・バックフィル・品質チェックを想定した設計。
    - ETLResult dataclass を定義し公開（src/kabusys/data/etl.py で再エクスポート）。
      - ETL 実行結果の集約（取得件数、保存件数、品質問題、エラー等）。
      - has_errors / has_quality_errors プロパティ、to_dict シリアライズを提供。
    - DuckDB 互換性やテーブル存在チェック、最大日付取得ユーティリティ等を用意。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）を追加。
    - market_calendar テーブルに基づく営業日判定ロジック:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
      - DB 登録値優先、未登録日は曜日ベースでフォールバック。
      - 最大探索日数制限 (_MAX_SEARCH_DAYS)、先読み／バックフィル、健全性チェックを実装。
    - calendar_update_job: J-Quants API から差分取得して冪等的に保存する夜間ジョブ（フェイルセーフ設計）。
  - ETL の実装方針・制約（DuckDB の executemany の空リスト制約等）について考慮。

- 研究（Research）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Volatility（20日 ATR、出来高等）、Value（PER、ROE）を計算する関数を実装:
      - calc_momentum, calc_volatility, calc_value を提供。
    - DuckDB を用いた SQL ベースの実装で、過度な外部依存を排除。
  - 特徴量探索・統計ユーティリティを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算: calc_forward_returns（任意ホライズン対応、入力検証）
    - IC（Information Coefficient）計算: calc_ic（スピアマンランク相関）
    - ランク変換ユーティリティ: rank（同順位は平均ランクで処理、丸めによる ties 対策）
    - ファクター統計サマリ: factor_summary（count/mean/std/min/max/median）
  - research パッケージ __init__ による公開 API を整備（zscore_normalize の提供元参照を含む）。

- AI / NLP（モデルを利用したスコアリング）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）を追加。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事抽出ロジック（calc_news_window, _fetch_articles）。
    - 銘柄ごとに記事を集約し、トリムして OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価（最大 20 銘柄 / チャンク）。
    - リトライロジック（429 / ネットワーク断 / タイムアウト / 5xx）を実装（指数バックオフ）。
    - レスポンスのバリデーションと復元処理（JSON 抽出、results キー検証、スコア数値化、±1.0 でクリップ）。
    - 部分成功時に既存スコアを保護するため対象コードのみ DELETE→INSERT する冪等書き込みを実装。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）を追加。
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースの抽出、OpenAI 呼び出し、リトライ、スコア合成、閾値判定を実装。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とフェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - LLM 呼び出しは news_nlp 側と意図的に別実装とし、モジュール結合を低減。
  - ai パッケージ __init__ で score_news を公開。

### 設計上の配慮 / その他
- ルックアヘッドバイアス防止:
  - 各種処理で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - prices_daily 等のクエリで target_date 未満 / 排他条件を明確にしている点を明記。
- 失敗モードのフェイルセーフ設計:
  - AI API の失敗時に例外を投げずにスコア 0.0 を採用したり、処理をスキップして他コードを保護する等、運用時の頑健性を重視。
- DuckDB 互換性の考慮:
  - executemany に空リストを渡せない制約への対応など実運用環境に合わせた実装。
- テスト容易性:
  - OpenAI 呼び出し箇所を patch 可能にして単体テストを容易にする設計。

### 変更
- 初回リリースのため変更履歴は無し。

### 修正
- 初回リリースのため修正履歴は無し。

### 破壊的変更
- なし（初回リリース）。

脚注
----
- 本 CHANGELOG はリポジトリ内ソースコードの実装内容から推測して記載しています。将来的なリリースで機能追加・ API 変更・バグフィックスが行われた場合は本ファイルを更新してください。