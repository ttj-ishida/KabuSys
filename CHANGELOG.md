Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。日付は YYYY-MM-DD 形式です。

当リポジトリはバージョン管理されたライブラリ／ツール群であり、
主に日本株のデータ取得・ETL、ファクター計算、ニュースの NLP スコアリング、
市場レジーム判定、マーケットカレンダー管理などを提供します。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-04
------------------

Added
- パッケージ初期リリース。主要機能と公開 API を追加。
  - src/kabusys/__init__.py
    - パッケージバージョンを "0.1.0" として設定。
    - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に定義。
  - 環境設定・自動 .env ロード機能を追加（src/kabusys/config.py）
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）。
    - export KEY=val 形式やクォート・インラインコメントのパースに対応する堅牢なパーサを実装。
    - Settings クラスを公開し、J-Quants / kabu ステーション / LINE / DB /監視関連などの設定項目をプロパティとして提供。
    - 必須環境変数未設定時は明示的な ValueError を送出する _require 実装。
    - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）を実装。
  - AI 関連モジュールを追加（src/kabusys/ai）
    - news_nlp.score_news: raw_news / news_symbols から銘柄毎に記事を集約して OpenAI（gpt-4o-mini）でセンチメントを取得し ai_scores テーブルへ書き込む。
      - JST ベースのニュース収集ウィンドウ計算（前日 15:00 ～ 当日 08:30 JST）を提供。
      - 1銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）やバッチ処理（最大20銘柄/コール）を実装。
      - JSON Mode 応答をバリデーションし、スコアを ±1.0 にクリップ。
      - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライし、その他はスキップして継続するフェイルセーフ設計。
      - DuckDB 互換性のため executemany 空リスト回避などの実装を反映。
    - regime_detector.score_regime: ETF(1321) の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を計算し market_regime テーブルへ冪等書き込み。
      - マクロニュース抽出（マクロキーワードリスト）→ OpenAI による JSON スコア取得 → 合成スコアのクリップ。
      - API 呼び出しのリトライ実装、失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
      - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターン、例外時は ROLLBACK を行う。
    - AI モジュールはテスト容易性のため OpenAI 呼び出し箇所を差し替え可能に設計（内部 _call_openai_api を patch できる）。
  - Research モジュールを追加（src/kabusys/research）
    - factor_research: calc_momentum, calc_volatility, calc_value を追加。
      - Momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
      - Volatility & Liquidity: 20日 ATR、ATR比率、20日平均売買代金、当日出来高比率。
      - Value: PER（EPS が 0/欠損なら None）、ROE（raw_financials から最新報告を取得）。
      - DuckDB SQL とウィンドウ関数を活用した高効率実装。外部 API 非依存。
    - feature_exploration: calc_forward_returns, calc_ic（Spearman）、factor_summary、rank を追加。
      - 将来リターン計算は複数ホライズンを一度のクエリで取得。horizons のバリデーションを実施。
      - IC 計算はランク（同順位は平均ランク）を使った Spearman を実装し、データ不足（<3）なら None を返す。
      - 統計サマリーは count/mean/std/min/max/median を提供。
    - research パッケージの __all__ を定義し、主要関数を再エクスポート。
    - zscore_normalize は data.stats から再エクスポート。
  - Data モジュールを追加（src/kabusys/data）
    - calendar_management: JPX マーケットカレンダー管理と営業日判定ロジックを提供。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
      - market_calendar が未取得のときは曜日ベースでフォールバック。
      - night batch job calendar_update_job を実装し、J-Quants からの差分取得→保存（バックフィル・健全性チェックあり）。
    - pipeline & etl: ETLResult（データクラス）と ETL パイプラインの基礎を追加。
      - 差分取得、保存（idempotent）、品質チェック（quality モジュール）を想定した設計。
      - ETLResult.to_dict により品質問題を辞書化して監査ログ等に利用可能。
    - data パッケージから ETLResult を再エクスポート（src/kabusys/data/etl.py）。
  - パッケージ間の公開 API を整備（__all__ による明示的エクスポート）。

Changed
- 初期公開のため既存設計方針をドキュメント内コメントとして多数追加（各モジュールに設計上の注意点とフェイルセーフ挙動を明記）。
  - 特にルックアヘッドバイアス回避のため datetime.today()/date.today() を内部ロジックで直接参照しない設計を強調。
  - DuckDB のバージョン差異を吸収するための実装（executemany の空リスト回避、リスト型バインド回避）を反映。

Fixed
- （初回リリース）内部ロジックやエラー処理の堅牢化を含む多数の実装上の注意点を反映（詳細は各モジュールのログメッセージ・例外処理を参照）。

Security
- OpenAI API キー取り扱い: api_key を引数で注入可能にし、未設定時は明示的に例外を投げることで誤設定に早期気付けるように設計。
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能。OS 環境変数は protected として上書きを防止。

Notes / Implementation details
- OpenAI との対話は gpt-4o-mini と JSON Mode を使用する前提。レスポンスのパース/バリデーション/クリップを確実に行う実装。
- API 呼び出しは RateLimitError・APIConnectionError・APITimeoutError・5xx をリトライ対象とし、その他のエラーはスキップして継続する方針（フェイルセーフ）。
- DuckDB をデータレイヤに採用。SQL はウィンドウ関数・ROW_NUMBER 等を活用して効率よく集計。
- DB 書き込みは基本的に冪等性を重視（DELETE→INSERT、ON CONFLICT 方針に準拠する設計など）。
- テスト容易性のため API 呼び出しの抽象化（モジュール内 private 関数の patch を想定）。

Acknowledgements
- 本リリースは設計仕様（StrategyModel.md / DataPlatform.md）に基づいて実装されています（コメントとして各モジュールに参照を明記）。

Deprecated
- （なし）

Removed
- （なし）

References
- ソース内ドキュメントとログメッセージを一次情報源として機能を推定・記載しています。具体的な利用方法やマイグレーション手順は README や別途ドキュメントで追記してください。