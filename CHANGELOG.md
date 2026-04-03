CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
安定化・互換性のためにセマンティックバージョニングを使用しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-03
--------------------

Added
- 初版リリース。kabusys パッケージの基礎機能を追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。
  - 環境設定 / ロード
    - src/kabusys/config.py
      - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
      - .env と .env.local の読み込み順序を実装（.env.local が優先）。OS 環境変数は保護され、上書きを防止する仕組みを導入。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動読み込み無効化に対応。
      - シェル風の export プレフィックスやシングル／ダブルクォート、エスケープ、インラインコメント等に対応した .env パーサ実装。
      - Settings クラスとしてアプリケーション設定を提供（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 等のプロパティ）。必須値未設定時は明示的なエラーを発生。
      - KABUSYS_ENV / LOG_LEVEL の検証（許容値の制約）とユーティリティプロパティ（is_live/is_paper/is_dev）。
  - AI（ニュース NLP / 市場レジーム判定）
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を算出、ai_scores テーブルへ書き込む処理を実装。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正しく計算する calc_news_window を実装（UTC 変換を内部で扱う）。
      - 1 銘柄あたり最大記事数／文字数のトリム、バッチサイズ制御（最大 20 銘柄／コール）、JSON Mode 応答検証、スコアクリップ（±1.0）、堅牢なレスポンス検証を実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ実装。API 失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
      - テストのために OpenAI 呼び出しを差し替え可能（_call_openai_api のモック化を想定）。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200 日移動平均乖離（重み 70%）と、news_nlp を用いたマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
      - マクロ記事フィルタ（キーワードリスト）取得、OpenAI 呼び出し（gpt-4o-mini）の堅牢化（リトライ、5xx の扱い、パース失敗フォールバック macro_sentiment=0.0）。
      - ルックアヘッドバイアスを避ける設計（target_date 未満のみ使用、datetime.today() を参照しない）。
  - Data（ETL / カレンダー管理）
    - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
      - ETL パイプラインの骨組みを実装（差分取得、保存、品質チェックの流れ）。ETLResult データクラスを公開（target_date、取得/保存件数、品質問題、エラーの集約）。
      - DuckDB を前提としたテーブル存在チェック、最大日付取得、部分失敗時の既存データ保護（削除→挿入の手順）などの互換性配慮。
    - src/kabusys/data/calendar_management.py
      - JPX カレンダーの夜間更新処理（calendar_update_job）と、営業日判定ユーティリティ（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）を実装。
      - market_calendar が未取得の場合の曜日ベースフォールバック、DB 登録値優先の一貫性、探索上限（_MAX_SEARCH_DAYS）など安全設計を導入。
  - Research（ファクター計算 / 特徴量探索）
    - src/kabusys/research/factor_research.py
      - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）等のファクター計算関数を実装（DuckDB SQL による高速集計）。
      - 欠損・データ不足時の挙動を定義（必要データ不足時は None）。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
      - 外部ライブラリに依存せず標準ライブラリ＋DuckDB で実装。
  - パッケージ公開 API
    - ai モジュールの score_news / score_regime、research モジュールの各種計算関数、data.pipeline の ETLResult、calendar_update_job などを外部から使用可能に公開。
  - ロギングとエラー処理
    - 各モジュールで詳細な info/warning/debug ログを追加。DB トランザクション時の ROLLBACK 保護とログ通知。
    - 明示的なフェイルセーフ（API エラー→0/スキップ）ポリシーを採用し、部分失敗が他機能に波及しないように設計。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 環境変数読み込み時に OS 環境変数を保護する仕組みを導入（.env による上書きを防止）。  
- OpenAI API キーや J-Quants のリフレッシュトークン等は Settings 経由で必須チェックを行い、未設定時に明示的なエラーを出す。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
  - OPENAI_API_KEY（AI 機能を利用する場合）
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで有用）。
- News / Regime の AI 呼び出しは OpenAI のレスポンスに依存するため、テスト時は各モジュールの _call_openai_api をモックして挙動を安定化させてください。
- DuckDB のバージョン依存（executemany に空リスト不可等）を考慮した実装済み。運用環境では DuckDB の互換性を確認してください。

今後の予定
- strategy / execution / monitoring モジュールの具体実装（パッケージ __all__ に準備済み）。
- テストカバレッジ強化、CI 用の DB フィクスチャ追加。
- リアルタイム監視・アラート機能の拡充。

----