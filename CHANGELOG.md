CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-01
------------------

Added
- 初期リリースを公開。
- パッケージ全体の公開 API を追加。
  - パッケージルート: kabusys.__version__ = "0.1.0"
  - __all__ に data, strategy, execution, monitoring を定義。
- 環境設定管理モジュールを追加 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは export KEY=val 形式、クォート内のバックスラッシュエスケープ、行末コメント処理等に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベースパス / 監視閾値 / 実行環境・ログレベル等をプロパティで取得。
  - 環境値のバリデーション: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）のチェック。
  - 必須環境変数未設定時は ValueError を送出する _require() を採用。
- AI（自然言語処理）モジュール群を追加 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとにニューステキストを結合し、OpenAI (gpt-4o-mini, JSON Mode) に投げてセンチメントスコアを生成。
    - チャンク処理 (最大 _BATCH_SIZE=20 銘柄) と 1 銘柄当たりの記事数/文字数上限を導入（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - API エラー（429/ネットワーク断/タイムアウト/5xx）に対して指数バックオフでリトライし、その他エラーはスキップするフェイルセーフ戦略を採用。
    - レスポンスの厳格なバリデーションと JSON 前後の余計なテキストを取り除く復元処理を実装。
    - スコアは ±1.0 にクリップ。スコアを書き込む際は対象コードのみ DELETE → INSERT して部分失敗時に既存データを保護。
    - datetime.today()/date.today() を使わず、外部から target_date を与えてルックアヘッドバイアスを防止。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次レジーム（bull/neutral/bear）判定。
    - LLM 呼び出しは独自実装でモジュール結合を避ける（news_nlp と内部関数を共有しない）。
    - データ不足時のデフォルト（ma200_ratio=1.0）や API 失敗時のフォールバック（macro_sentiment=0.0）などフェイルセーフを採用。
    - レジーム結果は market_regime テーブルへ冪等に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
- データ基盤モジュール群を追加 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの差分取得・夜間バッチ更新ジョブ calendar_update_job を提供（J-Quants クライアント経由）。
    - market_calendar が未取得の場合は曜日ベース（平日を営業日）でフォールバックする一貫した営業日ロジックを提供。
    - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day を提供し、DB 登録値を優先し未登録日は曜日で補完する設計。
    - 最大探索日数やバックフィル設定、健全性チェックを導入して安全性を確保。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを公開（取得件数・保存件数・品質チェック結果・エラー集約など）。
    - 差分取得、バックフィル、品質チェック（kabusys.data.quality 連携）などを想定した設計ドキュメントとユーティリティ。
    - jquants_client 経由の idempotent 保存（ON CONFLICT DO UPDATE）を想定。
- 研究（Research）モジュール群を追加 (kabusys.research)
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR・相対 ATR）、Value（PER/ROE）等のファクター計算関数を実装（DuckDB SQL による実装）。
    - データ不足時は None を返す等、安全な設計。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（Spearman）計算 calc_ic、ランク付けユーティリティ rank、統計サマリー factor_summary を実装。
    - pandas 等外部依存を持たず標準ライブラリで実装。
- research パッケージの __all__ で有用関数を再公開（zscore_normalize を含む）。

Changed
- 設計方針の強調:
  - 主要解析関数はルックアヘッドバイアスを避けるため内部で現在時刻を参照せず、常に外部から target_date を受け取る設計とした。
  - OpenAI 呼び出しは JSON Mode を利用し、厳密な構造での応答を期待する。パース失敗時は安全にスキップまたはフォールバック。
  - DuckDB に対する executemany の空リスト制約（DuckDB 0.10 等）を考慮した実装（空リスト時は実行をスキップ）。

Fixed
- 初期リリースに含まれる設計上の注意点・フェイルセーフを明示（API 失敗時のフォールバックや、DB 書き込み時のトランザクション管理、ROLLBACK の保護ログなど）。

Security
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を参照する方式にしており、キーの管理は呼び出し側に委ねる設計。

Notes / Known limitations
- OpenAI 依存: gpt-4o-mini を想定。JSON Mode の挙動に依存するため、モデル・API 仕様変更時の影響を受ける可能性あり。
- DuckDB バインドや executemany の挙動は DuckDB のバージョンにより差異があるため、実行環境での検証が必要。
- news_nlp と regime_detector はそれぞれ独立した OpenAI 呼び出し実装を持つ（モジュール間のプライベート関数共有を避けるため）。テスト時はそれぞれの _call_openai_api をモック可能。
- ETL の jquants_client / quality モジュールの具体実装は外部依存（本リポジトリ内で jquants_client の実実装を呼ぶ想定）。

Authors
- 初版実装（設計・コード）に基づく CHANGELOG を自動生成（コードベースの docstrings / 実装から推測して記載）。

-- End of CHANGELOG --