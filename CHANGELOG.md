CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

Unreleased
----------

（現在未リリースの変更はありません）

v0.1.0 - 2026-03-26
-------------------

Added
- 初版リリース（パッケージバージョン: 0.1.0）。
- パッケージ初期化
  - kabusys パッケージの公開 API を定義（__all__ = ["data", "strategy", "execution", "monitoring"]）。
- 設定/環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動ロード（優先順位: OS環境変数 > .env.local > .env）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - プロジェクトルート検出は .git または pyproject.toml を基準に探索（CWD に依存しない実装）。
  - .env パーサは export 文、クォート（シングル/ダブル）とバックスラッシュエスケープ、コメント扱いの細かい仕様に対応。
  - 環境設定ラッパー Settings を提供（必須キー取得の _require、各種プロパティ、既定値、値検証）。
  - 有効な環境値（development / paper_trading / live）やログレベルをバリデーション。
  - デフォルトの DB パス（DuckDB/SQLite）の設定と Path 変換を提供。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）で銘柄単位のセンチメント（-1.0〜1.0）を取得。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数上限 (_MAX_ARTICLES_PER_STOCK) と文字数上限 (_MAX_CHARS_PER_STOCK) を実装。
    - JSON Mode を利用した厳密な JSON 応答を期待しつつ、前後の余計なテキスト混入時の復元（外側の {} 抽出）やレスポンス検証ロジックを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフによるリトライ、その他の例外時はスキップして処理継続（フェイルセーフ）。
    - スコアは ±1.0 にクリップし、取得済みコードのみを DELETE → INSERT で置換して部分失敗時に既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei225 連動型）の 200 日移動平均乖離（重み 70%）と、ニュース NLP によるマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - LLM 呼び出しは記事がある場合のみ行い、API 失敗時は macro_sentiment=0.0（中立）にフォールバック。
    - レジームスコア合成、閾値判定、及び market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出しに対してリトライや 5xx の扱いを実装。
- Research（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、平均売買代金、出来高比率、PER/ROE（財務データに基づく）等の定量ファクター計算を実装。
    - DuckDB を用いた SQL ベースの計算を採用し、外部 API には依存しない設計。
    - データ不足時の None 処理やログ出力を含む堅牢な実装。
  - feature_exploration
    - 将来リターン（複数ホライズン）計算、Spearman ランク相関（IC）計算、ランク化ユーティリティ、ファクター統計サマリーを実装。
    - ties の扱いは平均ランクを採用し、浮動小数点の丸めで比較精度を担保。
    - horizons の入力検証（正の整数かつ <= 252）と SQL の効率的な生成。
- Data（kabusys.data）
  - calendar_management
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB にデータがない場合は曜日ベース（土日非営業）でフォールバックする一貫した挙動を提供。
    - 最大探索日数やバックフィル、健全性チェック（将来日付異常検出）などの安全策を実装。
    - calendar_update_job を実装し、J-Quants API からの差分取得と market_calendar の冪等保存を実行（バックフィルを含む）。
  - ETL / pipeline
    - ETLResult データクラスを公開（ETL 実行結果の構造化）。
    - 差分更新・バックフィル・品質チェック（quality モジュールを利用する想定）を考慮した ETL 設計方針を実装（pipeline 内で使用）。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。

Changed
- （初版のため該当なし）

Fixed
- OpenAI レスポンスの JSON パースや不正レスポンスに対する防御的処理を多数実装（news_nlp/regime_detector）。
- DB 書き込み時のトランザクション保護（COMMIT/ROLLBACK）と ROLLBACK 失敗時のログ出力を実装して安全性を高めた。
- DuckDB executemany の挙動差異（空リストでのエラー）を回避するため、空時チェックを追加。

Security
- OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数（OPENAI_API_KEY）から取得。未設定時は ValueError を発生させ明示的に失敗する。

Notes / 設計上の留意点
- ルックアヘッドバイアス対策として、date.today() / datetime.today() をスコア算出・ウィンドウ計算の基準に直接使用していない（target_date 引数ベースで計算）。
- LLM 呼び出し失敗時はフェイルセーフで中立なスコア（0.0）を採用し、パイプライン全体を停止させない設計。
- テスト補助として OpenAI 呼び出し箇所はパッチ可能な独立関数として実装。
- jquants_client など外部 API クライアントは data モジュールから利用する想定（実際の fetch/save 実装は別モジュール）。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡充と end-to-end テスト。
- ai モデルのプロンプト改善、レスポンス検証の強化、自動モニタリングの追加。
- ETL の並列化・パフォーマンス最適化と監査ログの強化。

お問い合わせ
- 不明点や誤記があればリポジトリの issue で報告してください。