CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（現在未リリースの変更はここに記載してください）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回公開リリース。
- パッケージ基本構成
  - パッケージ名: kabusys、バージョン 0.1.0。
  - export: data, strategy, execution, monitoring を __all__ で公開。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルートの検出は .git / pyproject.toml を利用、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応）。
  - .env パーサ実装（export KEY=val 形式対応、クォート値のバックスラッシュエスケープ対応、インラインコメント処理）。
  - .env 読み込み時の上書き制御（OS環境変数保護を考慮）。
  - Settings クラスを提供し、必須環境変数取得（_require により未設定時は ValueError）。J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルの取得ロジックを実装。
  - デフォルトの DB パス (duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db) を設定。
- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄センチメント（-1.0〜1.0）を算出。
    - バッチ処理で最大 20 銘柄/回、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - JSON Mode 出力の検証と堅牢なパース（前後余計なテキスト抽出処理あり）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装（最大リトライ回数設定）。
    - AI スコアを ai_scores テーブルへ置換的に書き込み（DELETE → INSERT、部分失敗時に他銘柄の既存スコアを保護）。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（_call_openai_api をモジュール内で定義）。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news からデータ取得、OpenAI（gpt-4o-mini）を用いたマクロセンチメント推定、スコア合成、market_regime への冪等書き込みを実施。
    - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - テスト容易化のため _call_openai_api は差し替え可能。
- リサーチ（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M・ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER・ROE）を DuckDB 上で計算する関数を提供。
    - データ不足時の扱い（必要行数未満は None）などを考慮。
  - feature_exploration モジュール
    - 将来リターン計算（任意ホライズン）、IC（スピアマンρ）計算、ファクター統計サマリ、ランク変換ユーティリティ（同順位は平均ランク）を実装。
    - pandas 等非依存で標準ライブラリ + DuckDB SQL による実装。
- データ基盤（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar テーブル）用のユーティリティを提供。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB にカレンダーデータがない場合は曜日ベースのフォールバック（週末除外）。
    - calendar_update_job により J-Quants API から差分取得 → market_calendar へ冪等保存を行う（バックフィル・健全性チェックを実装）。
  - ETL パイプライン（pipeline.py, etl.py）
    - ETLResult データクラスを定義し etl.py から再エクスポート。
    - 差分更新（最終取得日を基に差分のみ取得）、バックフィル、品質チェックのための骨組みを実装。
    - DuckDB テーブル存在チェック、最大日付取得などのユーティリティを提供。
- 安全性・堅牢性
  - DB 書き込みはトランザクションパターン（BEGIN / DELETE / INSERT / COMMIT）を採用し、例外時に ROLLBACK を試行。
  - DuckDB の executemany に関する互換性（空リスト回避）を考慮。
  - ルックアヘッドバイアス防止のため、内部処理で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す方式）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数に依存する機密情報（OpenAI API キー、J-Quants リフレッシュトークン、Kabu API パスワード、Slack トークン等）は Settings を通じて取得。未設定時は明示的に例外を送出して早期失敗させる設計。

既知の制限 / 注意点
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を前提。LLM レスポンスの不正やパースエラーが発生した場合は当該チャンクをスキップし、全体処理は継続する（フェイルセーフだが部分的にスコア欠落が発生する可能性あり）。
- news_nlp/regime_detector ともに OpenAI クライアントを作成して直接呼び出す設計のため、テスト時は _call_openai_api を patch して外部依存を切り離すことを推奨。
- 日時は UTC naive な datetime / date オブジェクトで扱う箇所がある（news ウィンドウ等は内部説明の通り JST ↔ UTC 変換を実装しているが、実運用では DB 側のタイムゾーン運用に注意）。
- research モジュールは prices_daily / raw_financials のみを参照し、本番の発注系 API を呼ばない設計。
- calendar_update_job は J-Quants クライアント（jquants_client）を呼び出すが、実行環境に応じた API 資格情報準備が必要。

---

脚注
- ドキュメント・ docstring に基づいて記載しています。実際の挙動（API レスポンス形式や DB スキーマの詳細）により動作が変わる箇所があります。実運用前に統合テストを実施してください。