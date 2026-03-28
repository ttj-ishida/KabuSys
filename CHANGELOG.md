Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

リリース日付の表記は YYYY-MM-DD です。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-28
-------------------

初回公開リリース。以下の主要機能・モジュールを追加しました。

Added
- パッケージ全体
  - kabusys パッケージを追加。__version__ = "0.1.0"。
  - モジュールのエクスポート整理（data, strategy, execution, monitoring を __all__ に設定）。

- 設定・環境管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env/.env.local の優先順位制御、OS環境変数の保護（protected set）と override オプション。
  - .env パースの堅牢化（export プレフィックス対応、クォート・エスケープ処理、コメント処理）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルなどのプロパティを公開。環境値検証（許容値チェック）を実装。

- AI（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を基にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む機能（score_news）。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を提供（calc_news_window）。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数制限、JSON モードレスポンスのバリデーション、429/ネットワーク/5xx のリトライ（指数バックオフ）を実装。
    - レスポンス検証・数値型変換・スコア ±1.0 でクリップ、部分成功時に既存スコアを保護する idempotent な DB 書き換え戦略（DELETE → INSERT）。
    - テスト用フック: _call_openai_api を patch して差し替え可能。

  - regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、市場レジーム（bull/neutral/bear）を日次で算出して market_regime テーブルへ書き込む機能（score_regime）。
    - MA200 比率計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロニュース抽出、OpenAI 呼び出し、合成スコアの閾値判定、冪等トランザクション処理を実装。
    - OpenAI 呼び出しは独立実装でモジュール結合を避け、API失敗時はマクロセンチメントを 0.0 とするフェイルセーフを採用。
    - API リトライ（429/ネットワーク/タイムアウト/5xx を想定）とログ出力。

- データ（kabusys.data）
  - calendar_management モジュール
    - market_calendar を使った営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録データを優先しつつ未登録日は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、保存）。
    - _MAX_SEARCH_DAYS 等の安全上限を導入して無限ループ防止。

  - pipeline / etl
    - ETLResult データクラス（ETL の取得数・保存数、品質問題、エラー一覧、状態判定プロパティ）を実装。
    - ETL パイプライン用ユーティリティ（差分更新、バックフィル、品質チェック統合、jquants_client を介した保存）を設計・実装する基盤を追加。
    - etl モジュールで pipeline.ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR（20日）などのファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。prices_daily / raw_financials を参照し、データ不足時の None ハンドリングを行う。
    - DuckDB を用いた SQL + Python 実装で、外部 API には依存しない設計。

  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）を実装。
    - IC（Information Coefficient：スピアマンの ρ）計算（calc_ic）とランク変換ユーティリティ（rank）。
    - ファクター統計サマリー（count/mean/std/min/max/median）を提供（factor_summary）。
    - Pandas 等への依存を避け、標準ライブラリと DuckDB のみで動作する設計。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Security
- OpenAI API キーは引数で注入可能。未設定時は ValueError を投げるため、誤動作を抑止。
- 環境自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で停止可能（テスト時の安全策）。

Notes / 実装上の注意・既知の制約
- OpenAI 呼び出しは gpt-4o-mini を想定しており、OpenAI SDK のバージョン差異に備えたエラーハンドリングを実装しているが、将来的な SDK 変更による影響がある可能性あり。
- DuckDB の executemany に空リストを渡せない点など、現行 DuckDB バージョンとの互換性を考慮した実装（空時は呼び出しをスキップ）。
- 日時の扱いは全て date / naive UTC datetime を用いる方針で、関数内部で datetime.today()/date.today() を直接参照しないようにしてルックアヘッドバイアスを回避している。
- 外部クライアント（J-Quants, OpenAI）は直接の I/O を伴うため、テスト時には _call_openai_api 等の関数を patch して差し替え可能。
- monitoring モジュールは __all__ に含まれるが、今回のコードスニペットに明示的な実装は含まれていません（今後の追加予定）。

Acknowledgements
- 初回リリースでカバーする設計方針や安全策（冪等性、フェイルセーフ、リトライ戦略、ルックアヘッド回避）を明確に実装しています。今後は各モジュールの単体テスト、ドキュメント補完、監視・運用機能の追加を推奨します。