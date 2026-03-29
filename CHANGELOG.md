# Changelog

すべての変更は Keep a Changelog の方針に従い記載しています。  
安定リリースはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-03-29

初期リリース。日本株自動売買プラットフォームのコア機能を提供します。以下はコードベースから推測される主要な追加・仕様です。

### 追加 (Added)
- パッケージのメタ情報
  - kabusys パッケージ初期バージョンを提供（__version__ = "0.1.0"）。
  - package-level の __all__ で主要サブパッケージを公開（data, strategy, execution, monitoring）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を読み込む自動ローダー実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）によりカレントワーキングディレクトリに依存しない自動読み込み。
  - 高度な .env パーサー実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数取得ラッパー Settings クラスを提供。J-Quants / kabu API / Slack / DB パスや実行環境（KABUSYS_ENV）・ログレベルの検証を含むプロパティを実装。
  - デフォルトの DB パス（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）を設定。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news / news_symbols を元に銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini）により銘柄ごとのセンチメントを -1.0〜1.0 で評価。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、1 銘柄あたりの最大記事数／文字数制限を実装。
    - JSON Mode を利用したレスポンス検証と堅牢なパース処理（余分なテキストの復元ロジック含む）。
    - API エラー（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフ付きリトライ、致命的でない失敗時はスキップして継続するフェイルセーフ設計。
    - ai_scores テーブルへ冪等的（DELETE → INSERT）に書き込む処理。
    - テスト用フック（_call_openai_api の差し替え）を考慮。

  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（比率）とマクロニュース（LLM によるセンチメント）の加重合成（70% / 30%）で日次レジーム（bull/neutral/bear）を判定。
    - calc_news_window と news_nlp の連携、OpenAI 呼び出しのリトライ・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。

- データ基盤（Data）モジュール (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - market_calendar テーブルを用いた営業日判定、翌営業日/前営業日探索、期間内営業日取得、SQ 日判定などのユーティリティを提供。
    - DB にカレンダーデータがない場合は曜日ベース（週末を休場）でフォールバックする設計。
    - calendar_update_job により J-Quants API からの差分取得と冪等保存（バックフィル・健全性チェック含む）を行うフローを実装。
  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを公開（etl.py で再エクスポート）。
    - 差分取得、保存（jquants_client 経由の idempotent 保存）、品質チェック（quality モジュール）を想定したパイプライン設計。
    - デフォルトのバックフィル日数やカレンダー先読みなどの設定定数を提供。
    - DuckDB 周りの互換性考慮（executemany での空リスト回避など）を含む実装。

- Research モジュール (src/kabusys/research)
  - ファクター計算 (factor_research.py)
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日ATR）、Value（PER, ROE）などの定量ファクターを計算する関数群を実装。
    - DuckDB 上で SQL を使いデータを取得し計算して結果を dict のリストで返す設計。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（任意ホライズン）、IC（Spearman の rank 相関）計算、rank/統計サマリー関数等を実装。
    - pandas 等外部ライブラリに依存しない純標準ライブラリ実装。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- API キーの取り扱い
  - OpenAI API キーやその他必須トークンは Settings を通じて取得し、未設定時は ValueError を発生させることで実行前に明示的な失敗を行う（誤った動作を避ける設計）。

### ドキュメント/実装上の注意事項（重要）
- OpenAI（gpt-4o-mini）の利用には API キーが必要。score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY のいずれかを必須とする。
- .env 自動ロードの挙動
  - OS 環境変数が優先され、.env ファイルは既存の OS 環境変数を上書きしない（.env.local は override=True で上書き可能だが OS 環境変数は保護される）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- DuckDB との相互運用性
  - executemany に空リストを渡すとエラーとなる DuckDB の仕様を回避するため、空チェックを行ってから executemany を実行している。
- ルックアヘッドバイアス対策
  - 日付関係の処理（ニュースウィンドウ、FACTOR 計算、regime 判定等）は内部で datetime.today()/date.today() を参照せず、target_date 引数に対して明確に計算する方針で実装している。
- フォールバック方針
  - API 呼び出し失敗時（LLM 等）は、可能な限り処理を続行し、スコアは 0.0 にフォールバックする等フェイルセーフ設計となっている（ただし部分的にスキップされる銘柄もありうる）。
- バージョンと互換性
  - settings.env / log_level の値検証があり、不正な値は ValueError を投げるため、CI/運用環境での環境変数値に注意が必要。

### 既知の制約・将来の改善候補（推定）
- J-Quants クライアント (jquants_client) と quality モジュールは外部依存想定で、実行環境に合わせた実装／モックが必要。
- 現バージョンでは PBR や配当利回りなどのバリュー指標は未実装（calc_value に注記あり）。
- OpenAI レスポンス形式は JSON Mode を前提としているが、実運用では追加のレスポンス検証やフォールバック方針をさらに強化する余地あり。

---

各機能の詳細な利用方法・API（関数引数や返り値、エラー仕様）はソースコードの docstring を参照してください。