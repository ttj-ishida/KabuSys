# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
バージョニングは SemVer を使用します。

注意: 以下はリポジトリ内ソースコードから推測して作成した変更履歴です。実際のコミット履歴を基にしたものではありません。

## [Unreleased]

### 追加予定 / TODO / 既知の問題
- pipeline モジュール末尾での実装途上（`_get_max_date` 関数の戻り処理にタイプミスや未完了箇所あり）。リファクタ・補完が必要。
- 外部クライアント（J-Quants / kabuステーション / OpenAI）の統合テストを追加予定。
- monitoring / execution / strategy パッケージの公開 API は __all__ に含まれているが、本CHANGELOG対象のコード断片では詳細実装が不足。今後の実装・ドキュメント整備を予定。
- セキュリティ注意: OpenAI / Slack / kabu API など外部トークンは環境変数必須。運用時はシークレット管理に注意。

---

## [0.1.0] - 2026-04-01

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py にてバージョン "0.1.0" を定義。
- 環境設定管理（src/kabusys/config.py）
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索し .env 自動読み込みを行う実装を追加。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行内コメント処理などに対応。
  - 自動ロード制御: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動読み込みを無効化可能。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境モード（development/paper_trading/live）等をプロパティとして取得可能。バリデーション付き（ログレベル/環境値の検査）。
  - 必須環境変数未設定時は ValueError を送出する `_require` を実装。
- AI モジュール（src/kabusys/ai）
  - ニュースNLP（src/kabusys/ai/news_nlp.py）
    - raw_news + news_symbols を銘柄別に集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を算出。
    - バッチ処理（最大 20 銘柄／チャンク）、1 銘柄あたりの記事数・文字数制限、JSON Mode 応答パース、レスポンス検証を実装。
    - 再試行ロジック: レート制限 (429) / ネットワーク断 / タイムアウト / 5xx の場合に指数バックオフでリトライ。非再試行エラーはスキップしてフェイルセーフにする設計。
    - レスポンスのバリデーションで未知コードを無視、スコアを ±1.0 にクリップ。
    - ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。部分失敗時に既存スコアを保護する実装。
    - テスト容易性のため OpenAI 呼び出し箇所を patch で差し替え可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）およびマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を算出・保存。
    - prices_daily および raw_news を参照。マクロキーワードに基づく記事抽出、OpenAI 呼び出し（gpt-4o-mini + JSON Mode）で macro_sentiment を算出。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ、リトライ・バックオフロジックを実装。
    - 計算結果は regime_score を -1.0〜1.0 にクリップし、ラベル（bull/neutral/bear）を付与して market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - lookahead バイアス防止のため datetime.today() 等を参照せず、target_date ベースでクエリ範囲を指定する設計。
- Research モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum ファクター算出（1M/3M/6M リターン、200 日 MA 乖離）、Volatility／Liquidity（20 日 ATR, avg turnover, volume ratio）、Value（PER, ROE）を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用して営業日ベースのラグや移動平均を算出。データ不足時の None 処理を実装。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン（任意ホライズン）算出（LEAD を利用）、IC（Spearman の ρ）計算、ランク変換（同順位は平均ランク）、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージの __init__ で主要関数を再エクスポート。
- Data モジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定 API（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を実装。
    - DB にデータがない場合は曜日ベースでフォールバック（週末を非営業日）。
    - calendar_update_job を実装し、J-Quants から差分取得 → market_calendar へ冪等保存（バックフィルと健全性チェック含む）。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを定義。ETL の取得数・保存数・品質問題・エラーを集約。
    - 差分取得・保存（jquants_client 経由）・品質チェック（quality モジュール）を想定した設計。バックフィルや健全性チェック、部分失敗時の保護設計を盛り込む。
    - etl.py で ETLResult を再エクスポート。
  - jquants_client による外部 API 呼び出し（参照のみ。具体実装は別モジュール想定）。
- その他
  - モジュール間の結合を低く保つ設計（例: OpenAI 呼び出しの private 関数を別モジュールで共有しない）。
  - DuckDB を主要なローカルデータベースとして使用する前提での実装。
  - ログ出力（logger）を広範に使用し、エラー発生時の情報やフェイルセーフ挙動を明示。

Changed
- 初期リリースのため該当なし（新規追加が中心）。

Fixed
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 外部サービスの API キーは環境変数経由で取得することを必須化。README / 運用ドキュメントでのシークレット管理推奨。

Notes / 実装上の設計方針（重要）
- ルックアヘッドバイアス防止: 全ての分析・スコアリング関数は target_date を引数に取り、内部で現在時刻を参照しない方針。
- DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT など）で実装。
- OpenAI など外部 API 呼び出しはリトライ/バックオフを実装し、失敗時はスコアをゼロまたはスキップして処理継続するフェイルセーフを採用。
- テスト容易性のため外部呼び出し（OpenAI 等）は patch や差し替えが可能なように実装。

----

作成者: ソースコード解析（自動推測）に基づく CHANGELOG（日本語）