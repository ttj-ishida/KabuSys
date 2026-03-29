Changelog
=========
すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

v0.1.0 - 2026-03-29
-------------------

初期リリース。日本株自動売買システム "KabuSys" のコアライブラリを公開します。

Added
- パッケージ情報
  - パッケージ初期化: kabusys.__version__ = 0.1.0、主要サブパッケージ（data, research, ai, ...）をエクスポート。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルと環境変数を統合して読み込む自動ローダーを実装（プロジェクトルートは .git または pyproject.toml から検出）。
  - .env のパースは export 形式、クォート、エスケープ、インラインコメントなど多様な記法に対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須変数取得ヘルパー _require を提供し、未設定時は ValueError を送出。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境（development, paper_trading, live）/ログレベルの取得を行う。env 値のバリデーション（許容値チェック）を実装。
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント (news_nlp.score_news)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価して ai_scores テーブルへ書き込む。
    - チャンクサイズ、文字数、記事数上限、リトライ（429/ネットワーク/5xx 用の指数バックオフ）などを考慮した堅牢な実装。
    - レスポンスの厳密なバリデーションとスコアクリップ（±1.0）。
    - テスト容易性のため _call_openai_api を差し替え可能。
    - タイムウィンドウは JST ベースで定義（前日 15:00 ～ 当日 08:30 JST）し、DB 側は UTC naive datetime を使用。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（Nikkei-225 連動）200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - DuckDB の prices_daily, raw_news, market_regime を使用。結果は冪等に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 失敗時は macro_sentiment=0.0 としてフォールバックするフェイルセーフ挙動。
    - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数を共有しない）でモジュール結合を低減。
    - 再試行ロジック、JSON パース保護、ログ出力を実装。

- データ（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーの保持と営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（土日は非営業日）。DB 登録があれば DB 値を優先。
    - 夜間バッチ job(calendar_update_job) で J-Quants から差分取得 → 保存。バックフィル、健全性チェック（将来日付の異常検出）あり。
    - 最大探索日数の上限を設け無限ループを防止。

  - ETL / パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（取得数・保存数・品質チェック・エラーの収集）。
    - 差分更新、backfill、品質チェック（quality モジュール経由）の設計方針を反映。
    - DuckDB 上での最大日付取得・テーブル存在チェック等のユーティリティを実装。

- リサーチ（kabusys.research）
  - ファクター計算（research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER/ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比率）を DuckDB の prices_daily / raw_financials を元に実装。
    - データ不足時は None を返すことで安全に扱える設計。
  - 特徴量探索（research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換ユーティリティ、ファクター統計サマリーを実装。
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB の SQL を活用。

- テスト・運用を意識した設計
  - API 呼び出し箇所（OpenAI）を簡単にモック差し替え可能にし単体テストを容易化。
  - ルックアヘッドバイアス防止: 各処理は datetime.today()/date.today() を直接参照せず、target_date ベースで計算。
  - DB 書き込みは冪等性を維持する（DELETE → INSERT など）ように設計。
  - DuckDB の executemany の制約（空パラメータ不可）に配慮した実装。

Known issues / Notes
- 未実装・意図的な制約
  - ファクター: PBR・配当利回りは現バージョンでは未実装（calc_value に注記あり）。
- 動作依存
  - DuckDB にテーブル（prices_daily, raw_news, market_calendar, raw_financials, news_symbols, ai_scores 等）が存在することを前提とする。
  - OpenAI API（gpt-4o-mini）を利用するため、OPENAI_API_KEY が必要。api_key を引数で注入可能。
- フォールバック挙動
  - ニュースや価格データが不足する場合、関数は None や 0.0 を返して処理を継続する設計（フェイルセーフ）。
- 環境変数ローディング
  - 自動ロードはプロジェクトルート検出に依存する。配布後の挙動を考慮して .env 自動ロードはオプトアウト可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- 日付/タイムゾーン
  - 全体的に date / UTC naive datetime を採用し、JST↔UTC の変換は明示的に行う（ニュースウィンドウ等）。

Security
- 現時点でセキュリティ関連の修正はなし。API キーやパスワードは環境変数経由で扱う設計。

Credits
- 初期実装: コードベースからの推測に基づく CHANGELOG。

(この CHANGELOG は配布されたソースコードの内容から推測して作成しています。実際のリリースノートとして使用する際は、リリース担当者による確認・加筆をお願いします。)