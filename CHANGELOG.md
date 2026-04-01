Keep a Changelogに従った CHANGELOG.md を日本語で作成しました。コードの内容から推測して記載しています。

注意:
- 日付は現時点（2026-04-01）をリリース日として使用しています（推定）。
- 記載はソースコードの実装・設計方針・ログメッセージ等から推測した変更点・機能群に基づきます。

CHANGELOG.md
=============

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠します。

[Unreleased]
------------

- 今後のリリースに向けた既知の変更はここに記載します。

[0.1.0] - 2026-04-01
--------------------

Added
- 基本パッケージ初期リリース（kabusys v0.1.0）。
  - パッケージ公開用の top-level 初期化: kabusys.__version__ = 0.1.0、主要サブパッケージを __all__ に公開。
- 環境設定/ロード機能（kabusys.config）
  - .env ファイルと環境変数からの設定読み込みを自動化（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env と .env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。
  - export KEY=val 形式、クォート／エスケープ、インラインコメントの取り扱いなどを考慮した .env パーサ実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト容易性）。
  - 必須設定取得ヘルパー _require と Settings クラスを提供。J-Quants / kabuステーション / Slack / DB /監視/システム関連設定プロパティを実装。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
- AI 関連機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を取得。
    - チャンク処理（最大 20 銘柄/リクエスト）、1銘柄あたりの記事数上限・文字数トリムなどトークン肥大化対策。
    - OpenAI の 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。その他エラーはスキップして処理継続（フェイルセーフ）。
    - レスポンスの厳格なバリデーション（JSON 抽出、results リスト、code の照合、スコア数値チェック）と ±1.0 でのクリップ。
    - 書き込みは部分失敗に備えた idempotent な置換戦略（特定コードのみ DELETE → INSERT）。
    - テストしやすさのため、内部の OpenAI 呼び出し関数をモック可能に設計。
    - calc_news_window によるニュース収集ウィンドウ（JST基準の前日15:00〜当日08:30、UTC変換）実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を統合して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの MA 計算、raw_news からマクロキーワードでの抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価、スコア合成、market_regime への冪等書き込みを実装。
    - API 呼び出しの再試行・エラー処理、パース失敗時のフォールバック（macro_sentiment=0.0）を含む堅牢化。
    - モジュール間結合を避けるため、OpenAI 呼び出しはニュース NLP と別実装で提供。テスト用に差し替え可能。
- データ処理・ETL（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラスを提供（取得件数・保存件数・品質問題・エラーの集約、has_errors / has_quality_errors / to_dict）。
    - 差分更新・バックフィル・品質チェックのための設計（J-Quants API 経由の差分取得、保存は idempotent）。
    - DuckDB 周りの互換性を考慮したユーティリティ（テーブル存在確認、最大日付取得など）。
  - calendar_management（JPX マーケットカレンダー管理）
    - market_calendar を用いた営業日判定 API（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。最大探索日数制限で安全性確保。
    - 夜間バッチ更新 job（calendar_update_job）で J-Quants から差分取得・保存・バックフィル・健全性チェックを実装。
  - ETL 公開インターフェースの再エクスポート（kabusys.data.etl が ETLResult を再エクスポート）。
  - jquants_client 経由の取得/保存処理を想定した設計。
- 研究用ユーティリティ（kabusys.research）
  - factor_research（calc_momentum / calc_volatility / calc_value）
    - StrategyModel に基づくファクター計算を DuckDB SQL で実装（mom_1m/3m/6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe 等）。
    - データ不足時の None 処理、結果を (date, code) キーの辞書リストで返す。
  - feature_exploration（calc_forward_returns / calc_ic / factor_summary / rank）
    - 将来リターン計算（任意ホライズン、入力検証）、スピアマン IC の計算、ファクター統計要約、ランク処理（同順位は平均ランク）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
- ロギングと設計方針
  - 重要処理における詳細ログ（info/warning/debug）を追加しトラブルシュートを容易化。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計方針を明示。
  - DuckDB 互換性（executemany に空リスト不可など）への配慮を実装。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Security
- OpenAI API キーや他の必須機密情報が未設定の場合、明示的に ValueError を投げることで誤動作を防止する設計。
- 環境変数読み込みで OS の既存環境変数を保護するための protected キーセットを導入。

Notes / 実装上の注意
- OpenAI への呼び出しは JSON Mode（response_format に json_object）を使用する想定。レスポンスが完全な JSON でない場合に備えた復元ロジックを実装。
- DuckDB 側の型や返り値形式（date 型等）に依存する箇所では変換ユーティリティを実装しているため、DB バージョン差異に注意。
- テスト容易性のため、OpenAI 呼び出し関数（_call_openai_api）や自動 .env ロードの無効化フラグを用意している。ユニットテストではこれらをモック/無効化してテスト可能。

今後の課題（推定）
- 実運用に向けての監視・アラート（monitoring）、実際の注文発注（execution）周りの統合作業および安全性テストの実施。
- ai_scores / market_regime などの DB スキーマ定義ドキュメントやマイグレーションスクリプトの整備。
- 性能改善（大規模データでの DuckDB クエリ最適化、OpenAI 呼び出しの並列化やレート管理）。
- より詳細な品質チェック・品質レポート機能の強化。

--- 

上記はコード中の実装・ログ・ドキュメンテーション文字列（docstring）から推測してまとめた CHANGELOG です。必要であれば、各項目をより細かく分割（モジュール別やファイル別）したり、実際のリリース日・変更履歴をプロジェクト実運用に合わせて調整できます。