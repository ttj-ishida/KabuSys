Keep a Changelog
=================

この変更履歴は "Keep a Changelog" のフォーマットに準拠します。  
日付はコードベースに含まれる実装から推測して記載しています。

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初期リリース。モジュール構成（kabusys、kabusys.ai、kabusys.data、kabusys.research）を提供。
- 環境設定管理
  - .env ファイルまたは環境変数から設定を読み込む settings（kabusys.config.Settings）を追加。
  - 自動ロード: パッケージ配置場所（.git または pyproject.toml を探索）を基準に .env / .env.local を自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パーサー実装: export KEY=val 形式、クォート内のバックスラッシュエスケープ対応、インラインコメント処理などをサポート。
  - OS 環境変数の保護（.env の上書きを抑止する protected set）。
  - 必須キー取得用の _require ヘルパーと各種設定プロパティ（J-Quants / kabu API / Slack / DB パス / 環境判定 / ログレベル 等）。
  - 有効値チェック（KABUSYS_ENV, LOG_LEVEL）。

- AI（自然言語処理）関連
  - ニュースセンチメント解析 (kabusys.ai.news_nlp)
    - target_date に基づくニュース収集ウィンドウ計算（calc_news_window）。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄単位のセンチメントを算出する score_news。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの最大記事数 / 最大文字数トリム、JSON Mode レスポンスのバリデーション／抽出、±1.0 のクリップ処理を実装。
    - API エラー（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフリトライ、非致命的なフォールバック（失敗時はスキップ・空辞書返却）を採用。
    - テスト用に OpenAI 呼び出しを差し替え可能（内部 _call_openai_api をパッチして置換）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
    - prices_daily / raw_news を参照、ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - API 呼び出し失敗時のフェイルセーフ（macro_sentiment=0.0）や再試行ロジックを実装。
    - モジュール間の結合を避けるため、news_nlp の内部呼び出し関数は共有せず独立実装。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを基に営業日判定 is_trading_day、SQ 判定 is_sq_day、翌営業日／前営業日 next_trading_day / prev_trading_day、期間内営業日取得 get_trading_days を実装。
    - market_calendar が未取得の場合は曜日ベース（週末を休日）でフォールバックする一貫したロジック。
    - 夜間バッチ更新 calendar_update_job: J-Quants から差分取得・バックフィルを行い market_calendar を冪等的に更新。健全性チェック（将来日付の過大チェック）を実装。

  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラス（pipeline.ETLResult）を導入し、実行結果（取得数/保存数/品質問題/エラー等）を表現。
    - 差分取得、バックフィル、品質チェックの設計方針を反映したパイプライン基盤の骨格を提供。
    - etl モジュールで ETLResult を再エクスポート。

  - DuckDB 関連ユーティリティ
    - テーブル存在チェックや最大日付取得などのヘルパーを実装（DuckDB 互換性を考慮）。
    - 各 DB 書き込みはトランザクション制御（BEGIN / COMMIT / ROLLBACK）により冪等性と安全性を確保。

- リサーチ（kabusys.research）
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算（prices_daily 前提）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比を計算。
    - calc_value: raw_financials の最新財務情報と結合して PER / ROE を計算。
    - 営業日／スキャン範囲のバッファ設計を考慮した SQL 実装。

  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（欠損や同値処理を考慮）。
    - rank: 同順位は平均ランクを返すランク化ロジック（丸めにより ties 検出の安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算する統計サマリー。

Changed / Design decisions
- ルックアヘッドバイアス対策
  - 全てのバッチ/スコアリング関数は datetime.today() / date.today() を直接参照せず、呼び出し側が target_date を渡す設計とした。
  - DB クエリは target_date 未満・以内等の境界を明確にしてルックアヘッドを防止。

- ロバスト性とフェイルセーフ
  - OpenAI API 呼び出しに対し、429/ネットワーク断/タイムアウト/5xx をリトライ対象にして指数バックオフを適用。致命的でないエラー時は例外を上位に投げずフォールバック（0.0 やスキップ）して処理継続する方針を採用。
  - JSON レスポンスのパースで失敗した場合、前後の余計なテキストを切り出して復元するフォールバックを実装。
  - DuckDB executemany の互換性を考慮し、空パラメータの実行を回避するチェックを導入。

- テスト容易性
  - OpenAI 呼び出しポイントを内部関数（_call_openai_api）で定義し、unittest.mock.patch による差し替えを想定した設計。

Fixed
- .env 読み込みでの I/O エラーは警告で処理を継続するように調整（環境による失敗がアプリを停止させない）。
- market_regime / ai_scores 等への書き込みは冪等化（DELETE → INSERT）して部分失敗時に既存データを不必要に消さないように改善。
- news_nlp / regime_detector での API エラー時のログ出力を明確化し、リトライ回数消費後は安全値で継続するように変更。

Security
- 外部 API キー（OpenAI）は引数経由または環境変数 OPENAI_API_KEY を使用する設計。キーのログ出力等は行わない方針。

Notes / Known limitations
- 現時点では本パッケージは主にデータ処理・分析・スコアリングの基盤を提供するもので、実際の発注（execution）やモニタリング（monitoring）の詳細な実装は別モジュールで扱う想定。
- J-Quants / kabu API クライアント実装（jquants_client など）は別モジュールとして参照しているため、外部 API のレスポンス仕様変更は影響を与える可能性がある。
- PBR・配当利回りなど一部バリューファクターは未実装。

参考
- パッケージ初期バージョン番号は src/kabusys/__init__.py にて __version__ = "0.1.0" として定義されています。