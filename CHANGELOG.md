CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在の日付: 2026-03-29

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初回公開（kabusys v0.1.0）。
- パッケージ公開情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加し、data/strategy/execution/monitoring を公開対象とする __all__ を定義。
- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local からの自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml から検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - export KEY=val 形式・クォート・コメントを考慮した堅牢な .env パース実装。
    - 既存 OS 環境変数を保護する protected オプション。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの取得・検証を実装。
    - 必須環境変数未設定時に ValueError を送出する _require ヘルパー。
- AI モジュール（ニュース NLP / 市場レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - チャンク処理（最大 20 銘柄）、1 銘柄あたりの記事数・文字数上限、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライ。
    - JSON Mode 応答のバリデーション処理（部分的な余分テキストの復元含む）とスコアクリップ（±1.0）。
    - DuckDB への冪等書き込み（DELETE → INSERT のトランザクション）と部分失敗時の既存データ保護。
    - テスト容易性のため _call_openai_api を分離してモック可能に実装。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照して ma200_ratio を計算、ニュースはマクロキーワードで抽出し LLM に投げる。
    - API 失敗時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ、レスポンス JSON の堅牢なパースとリトライ処理。
    - 結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - news_nlp と内部実装を共有せず、独立した _call_openai_api を使用することでモジュール間結合を低減。
- Data（ETL / パイプライン / カレンダー）
  - src/kabusys/data/pipeline.py, etl.py
    - ETLResult dataclass を定義し、ETL の収集結果（取得数・保存数・品質問題・エラー）を構造化。
    - 差分取得・バックフィル・品質チェックの設計に基づくユーティリティ関数（テーブル存在チェック、最大日付取得など）。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar がない場合の曜日ベースフォールバック、DB 登録優先の一貫した判定ロジック、最大探索日数による無限ループ防止。
    - calendar_update_job による J-Quants からの差分取得および冪等保存の実装（バックフィル・健全性チェック含む）。
- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR、相対 ATR、出来高関連）、バリュー（PER、ROE）を DuckDB の SQL で計算する関数を実装。
    - データ不足時の None ハンドリング、ログ出力を含む。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（horizons: デフォルト [1,5,21]）を一度のクエリで取得する実装。
    - IC（Spearman の ρ）計算、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を提供。
    - 外部ライブラリに依存せず標準ライブラリのみでの実装を採用。
- 内部ユーティリティ・互換性対応
  - DuckDB の executemany に関する挙動（空リスト不可）を考慮した実装。
  - すべてのアルゴリズムで datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。
  - ロギングとエラー時のロールバック/警告ログ出力を多用した堅牢化。

Changed
- 初版のため該当なし（ベース実装）。

Fixed
- 初版のため該当なし（ベース実装）。

Security
- OpenAI / J-Quants 等外部 API キーは環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN 等）経由で注入する設計。Settings._require による必須チェックを実装。
- .env パースでのエスケープやクォート処理を注意して扱い、意図しない変数注入やトークン破壊を最小化。

Notes / 開発上の注意
- 本バージョンは多くのコンポーネントで DuckDB と OpenAI SDK (openai) に依存します。実行環境にインストールされていることを確認してください。
- AI 部分は gpt-4o-mini を想定したプロンプト設計を行っており、レスポンスは JSON モードで受け取る前提です。
- 一部の関数（_call_openai_api 等）はテスト時にモック可能に分離されています。ユニットテストを書く際はこれらを差し替えてください。

Authors
- コードベースの内容から推測して自動生成された CHANGELOG です。実際の貢献者やコミット履歴に基づく正確な変更履歴はリポジトリのコミットログを参照してください。