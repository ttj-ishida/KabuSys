CHANGELOG
=========

このファイルは Keep a Changelog の形式に従って記載しています。
<https://keepachangelog.com/ja/1.0.0/>

ルール:
- すべての注目に値する変更はこのファイルに記録します。
- 既知の互換性の破壊は明示します。

Unreleased
----------

（なし）

0.1.0 - 2026-04-09
------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基礎機能を実装。
  - パッケージ公開情報
    - src/kabusys/__init__.py に __version__="0.1.0"、主要サブパッケージを公開（data, strategy, execution, monitoring）。
  - 設定/環境変数管理
    - src/kabusys/config.py
      - .env / .env.local をプロジェクトルートから自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
      - .env のパースは export 形式、シングル/ダブルクォートとエスケープ、インラインコメントを考慮した堅牢な実装。
      - 各種設定プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / paper trading 設定 / 監視閾値 / ログレベル / 環境判定など）。
      - 設定値のバリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。
  - AI（NLP）関連
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols を元に銘柄単位のニュース集約 -> OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメントを ai_scores に書き込む処理を実装。
      - タイムウィンドウ計算（前日15:00 JST～当日08:30 JST 相当）、記事トリム、チャンク送信（最大 20 銘柄/回）、JSON Mode 応答のバリデーション、スコア ±1.0 クリップ。
      - 再試行（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフ、API 失敗時はフェイルセーフでスキップ。
      - テスト容易性のため _call_openai_api を patch で差し替え可能。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime に冪等書き込み。
      - マクロ記事抽出（キーワードベース）、OpenAI 呼び出し、リトライ/フェイルセーフ、レジームスコア合成ロジックを実装。
  - Data（ETL / カレンダー / パイプライン）
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理ロジック（market_calendar の DB 優先・不足時は曜日フォールバック）、営業日判定・次/前営業日・期間内営業日列挙・SQ 判定、夜間バッチ更新ジョブ（J-Quants から差分取得し保存）を実装。
      - 最大探索上限やバックフィル、健全性チェックを導入して安全性を担保。
    - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
      - ETL 処理の設計と ETLResult データクラスを実装。差分取得、idempotent 保存（save_* を利用）、品質チェックの結果収集を想定。
      - ETLResult に has_errors / has_quality_errors / to_dict を実装し監査・デバッグ用に変換可能。
    - src/kabusys/data/__init__.py と関連モジュールの公開インターフェース整備（ETLResult の再エクスポートなど）。
  - Research（ファクター計算・特徴探索）
    - src/kabusys/research/factor_research.py
      - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR）、Value（PER, ROE）等のファクター計算を実装。DuckDB の SQL ウィンドウ関数を活用し、データ不足時の None 処理やログ出力を行う。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（任意 horizons、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク変換、ファクター統計サマリを実装。外部依存を持たない純 Python 実装。
    - src/kabusys/research/__init__.py で主要関数を再エクスポート。
  - その他ユーティリティ
    - ロギングと入力検証を各所で強化（例: OpenAI API キー未設定時は明確な ValueError）。
    - DuckDB を前提とした SQL 実装（日付変換・NULL 管理に配慮）。
    - テスト容易性: OpenAI 呼び出しをモジュール単位で差し替え可能、環境自動読み込みを無効化できる等。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の自動ロード時に既存 OS 環境変数を保護する仕組み（protected set）を導入。.env.local は既存 OS 環境変数を上書きできるが protected による保護が可能。

Notes / Migration
- OpenAI 関連
  - 各 AI 関数（score_news, score_regime）は api_key 引数で API キーを注入でき、引数が None の場合は環境変数 OPENAI_API_KEY を参照します。実行前に API キーを設定してください。
  - デフォルトモデルは gpt-4o-mini。レスポンスは JSON Mode を前提にしているため、モデル応答形式に注意してください。
- 環境/設定
  - .env, .env.local をプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から自動的に読み込みます。パッケージ化・デプロイ後に挙動を変えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
  - 設定のバリデーションにより不正な値は ValueError を送出します（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。既存運用で値が異なる場合は見直しが必要です。
- DB 書き込み
  - ai_scores / market_regime などへの書き込みは冪等性を考慮した削除→挿入の方式を採用しています。部分失敗時でも他コードの既存スコアを保護する設計です。
- テスト
  - OpenAI 呼び出しや自動 .env 読み込みはテスト時に差し替え・無効化できるよう設計されています（unittest.mock.patch、KABUSYS_DISABLE_AUTO_ENV_LOAD）。

互換性の破壊（Breaking Changes）
- 初回リリースのため該当なし。

今後の予定（例）
- strategy / execution / monitoring パッケージの実装拡充（バックテスト・実取引ロジック・監視アラート）。
- AI モデルの切替・プロンプト改善によるスコア精度向上。
- ETL 品質チェックの詳細ルール拡張と自動修正機能。

---

注: 本 CHANGELOG は提示されたコードから推測して作成したものであり、実際のコミット履歴や外部 API 実装の詳細を反映していない可能性があります。必要であればリポジトリのコミットログやリリースノートに合わせて調整します。