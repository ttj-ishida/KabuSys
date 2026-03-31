Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは "Keep a Changelog" の形式に従っています。

v0.1.0 - 2026-03-31
-------------------

初回リリース。日本株自動売買／リサーチ／データ基盤のためのコア機能を実装しました。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（src/kabusys/__init__.py にて __version__="0.1.0" を設定）。
  - 外部公開モジュール群: data, research, ai, その他のサブパッケージを公開。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env 解析における詳細挙動:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理。
    - コメント処理（クォート外・直前空白判定での '#' 処理）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスによる環境変数ラッパー（J-Quants / kabuステーション / Slack / DBパス / 環境種別 / ログレベルなどのプロパティ）。
  - デフォルトのデータベースパス（DUCKDB_PATH, SQLITE_PATH）を用意。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとのテキストを作成して OpenAI (gpt-4o-mini) に JSON モードで送信。
    - バッチ処理: 1 コールあたり最大 20 銘柄、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - リトライ／バックオフ: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフで再試行。
    - レスポンスの厳密バリデーション（JSON 抽出、results 配列の検証、コード照合、スコア数値チェック）。
    - スコアは ±1.0 にクリップ。
    - 書込みは部分失敗に強い挙動（取得できた銘柄のみ DELETE→INSERT で置換）。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - 単体テスト用に _call_openai_api を差し替え可能な設計。
    - calc_news_window ユーティリティ（JST ベースのニュースウィンドウ計算）を公開。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジームを判定（'bull' / 'neutral' / 'bear'）。
    - prices_daily と raw_news を参照し、ma200_ratio 計算・マクロ記事抽出・LLM 集計を実行。
    - LLM 呼び出しは独立実装（news_nlp とプライベート関数を共有しない）。
    - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - DB への書込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。
    - リトライ／エラー処理やログ出力を備える。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを扱うユーティリティ群を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日を休場扱い）。
    - カレンダー夜間更新ジョブ calendar_update_job（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索範囲の制限や異常時の保護（_MAX_SEARCH_DAYS, _SANITY_MAX_FUTURE_DAYS 等）。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（ターゲット日、取得/保存件数、品質問題・エラー集計など）。
    - 差分取得・バックフィル・品質チェックを想定した内部ユーティリティ（テーブル存在確認、最大日付取得等）。
    - ETLResult.to_dict により品質問題をサマリ化して出力可能。
    - data.etl で ETLResult を再エクスポート。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev の計算（営業日ベースのラグを使用）。
    - ボラティリティ／流動性: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - バリュー: PER（株価/EPS、EPS=0 で None）、ROE（raw_financials から最新レコードを取得）。
    - DuckDB SQL を活用した実装（prices_daily / raw_financials を参照）。
    - データ不足時の None 戻し、ログ出力。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
    - IC 計算 calc_ic（スピアマンのランク相関、サンプル不足時は None）。
    - rank（同順位は平均ランクで処理、浮動小数丸めで ties 対策）。
    - factor_summary（count/mean/std/min/max/median を算出）。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

Changed
- （初回リリースのため該当なし）

Fixed
- フェイルセーフ実装（AI API 失敗時に処理全体を止めない動作を明示）
  - news_nlp: API 呼び出し失敗時は該当チャンクをスキップし空辞書を返す。429/ネットワーク/5xx はリトライ。
  - regime_detector: API 全リトライ失敗時は macro_sentiment=0.0 として計算継続。
  - DB 書込み失敗時には ROLLBACK を試み、失敗時は警告ログ出力。

Security
- .env 自動読み込み時の既存 OS 環境変数保護（.env の上書きを防ぐ protected セットの導入）。
- 必須トークン取得時は明確な例外（ValueError）を発生させ、未設定のままの稼働を防止。

Notes
- 設計方針の強調
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() に依存しない設計を各 AI / スコアリング関数で採用（target_date を引数で受け取る）。
  - DuckDB を主要なローカル分析 DB として使用。DuckDB の executemany の挙動を考慮した実装（空リスト回避等）。
  - OpenAI への問い合わせは JSON Mode（response_format={"type": "json_object"}）とし、厳密なレスポンスバリデーションを行う。
  - テスト容易性のため、OpenAI 呼び出し箇所は差し替え可能（モジュール内 private 関数を patch してテスト可能）。
  - DB 書込みは可能な限り冪等性を担保（DELETE→INSERT、ON CONFLICT やトランザクション利用）。

Acknowledgements / External
- OpenAI API（gpt-4o-mini）を利用する想定の実装。API キーは api_key 引数または環境変数 OPENAI_API_KEY で注入可能。

未記載事項
- jquants_client の実装や kabu ステーション連携の具体的な発注ロジックはこのリリース範囲では参照のみ（モジュール呼び出しによる抽象的連携を行う実装）。

今後の予定（例）
- 追加のファクターや取引戦略の実装。
- モデル評価 (バックテスト) / パフォーマンス最適化。
- モジュール間のドキュメント拡充および API 安定化。