CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

[未リリース]: https://example.com/compare/HEAD...main

0.1.0 - 2026-03-29
-----------------

Added
- 初回公開リリース。
- パッケージエントリポイント
  - kabusys パッケージを公開。__version__ = "0.1.0"。パッケージ公開時に data / strategy / execution / monitoring を外部公開モジュールとして想定（__all__ に列挙）。
- 環境設定 & .env ローダー (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。プロジェクトルートは .git または pyproject.toml により決定するため、CWD に依存せずパッケージ配布後も動作。
  - .env パース処理は以下に対応:
    - 空行・コメント行（#）を無視
    - export KEY=val 形式をサポート
    - シングルクォート / ダブルクォートで囲まれた値内のバックスラッシュエスケープ対応
    - クォートなしの値は「# の直前がスペース/タブ」のときだけコメントとして扱うなど、シェル風の取り扱いを考慮
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。OS 環境変数を保護する protected オプションを導入。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト向け）。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や既定値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）をプロパティ経由で取得。KABUSYS_ENV / LOG_LEVEL の検証を実装（許容値チェック）。
- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントを算出。
    - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して扱う（ルックアヘッドバイアス回避）。
    - チャンク処理（デフォルト 20 銘柄/チャンク）、1銘柄あたりの記事数／文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトリム。
    - 429・ネットワーク断・タイムアウト・5xx サーバーエラーに対して指数バックオフでリトライ。その他エラーはスキップしフェイルセーフで継続。
    - レスポンスの厳密なバリデーション実装（JSON 抽出、results リスト、code/score の存在と型チェック、スコアの有限性検査、±1.0 クリップ）。
    - 書き込みは冪等性を考慮（取得済みコードのみ DELETE → INSERT）して部分失敗時に他銘柄の既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch できる設計）。
  - regime_detector.score_regime
    - ETF 1321 の直近 200 日終値から MA200 乖離（比率）を算出し（ルックアヘッド防止のため target_date 未満データのみ使用）、ニュース由来のマクロセンチメントと重み合成して市場レジーム（bull/neutral/bear）を算出。
    - マクロニュースは news_nlp.calc_news_window により同様のタイムウィンドウで抽出、OpenAI を用いて JSON レスポンスから macro_sentiment を取得。
    - 計算式と閾値（重み: MA 70% / マクロ 30%、スケール、閾値等）を定義。API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ。
    - market_regime への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に行い、例外時は ROLLBACK を試行。
- リサーチ（ファクター計算・特徴量探索）モジュール (kabusys.research)
  - factor_research: calc_momentum / calc_volatility / calc_value
    - Momentum: 1M/3M/6M リターンおよび MA200 乖離を計算。データ不足時は None を返却。
    - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。計算ウィンドウ・NULL の取り扱い（true_range の計算条件）に注意。
    - Value: raw_financials の最新報告を結合して PER / ROE を算出（EPS が 0 または欠損の場合は None）。
    - いずれも DuckDB 上で SQL ウィンドウ関数を活用して効率的に計算。
  - feature_exploration: calc_forward_returns / calc_ic / rank / factor_summary
    - 将来リターンを任意ホライズンで一括取得する SQL 実装（LEAD を利用）。
    - Spearman ランク相関（IC）を手計算で実装（同順位は平均ランク処理）。
    - factor_summary により count/mean/std/min/max/median を算出（None 除外）。
    - pandas 等に依存せず標準ライブラリで実装。
- データプラットフォーム（kabusys.data）
  - calendar_management
    - market_calendar の有無に応じた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベース（平日＝営業日）でフォールバック。最大探索範囲を設けて無限ループを防止。
    - calendar_update_job を実装し、J-Quants API（jquants_client）から差分取得 → 保存（バックフィル・健全性チェック含む）する夜間バッチ処理を提供。
  - pipeline / etl
    - ETLResult データクラスを公開（pipeline.ETLResult を etl モジュールで再エクスポート）。ETL 実行結果、品質チェック結果、エラー概要を保持し、dict 化もサポート。
    - ETL パイプライン設計に基づいた差分取得、保存、品質チェックの補助ユーティリティを提供（jquants_client / quality モジュールとの連携を想定）。
  - DuckDB のバージョン差異（executemany の空リスト扱いなど）を考慮した実装上の注意が明記されている。
- テストしやすさ・堅牢性
  - OpenAI 呼び出し箇所は内部関数を patch して差し替えられる設計（単体テストでのモックが容易）。
  - ルックアヘッドバイアスを避ける設計（date.today() 等を計算内部で直接参照しない）。
  - API 呼び出しの失敗に備えたフォールバック（0.0 やスキップ）やログ出力により、外部依存失敗がワークフロー全体を破壊しないように配慮。

Known issues / Limitations
- OpenAI（gpt-4o-mini）および J-Quants クライアントへの依存があるため、実行には対応する API キーや外部サービスへの接続が必要。
- jquants_client 等の外部依存モジュール本体はこの差分に含まれていない（インターフェースに依存）。
- DuckDB のバージョン差異（特に executemany / リストバインドの挙動）に注意。コード内で互換性対策を行っているが、環境によっては追加対処が必要。
- 一部ドキュメント（StrategyModel.md, DataPlatform.md 等）に依拠した実装方針がコメントに記載されているが、外部ドキュメント自体は本リリースに含まれない可能性あり。

Security
- 特になし（公開時点で既知のセキュリティ修正は含まれていません）。環境変数の取り扱いは OS 環境変数をデフォルトで保護する仕組みを導入。

詳細・開発者向けメモ
- 自動 .env ロードはプロジェクトルート検出に失敗した場合はスキップするため、配布パッケージ環境でも安全に動作しやすい。
- 多くの DB 書き込み処理は明示的な BEGIN / DELETE / INSERT / COMMIT パターンを採用し、例外時に ROLLBACK を試みている。
- AI レスポンスの堅牢な検証や部分書き込み戦略（失敗したチャンクがあっても他の銘柄データを保護）など、運用を想定した実装が盛り込まれている。

Copyright
- 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして使う際は実プロジェクトの運用者による確認・補正を推奨します。