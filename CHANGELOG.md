CHANGELOG
=========

全般ルール: この変更履歴は "Keep a Changelog" のスタイルに準拠しています。  
このリポジトリの初回リリースとして v0.1.0 を記載しています（パッケージ版の __version__=0.1.0 に基づく）。

[Unreleased]
------------

- （未リリースの変更はここに記載します）

0.1.0 - 初回リリース
-------------------

Added
- パッケージ初期構成を追加
  - パッケージ名: kabusys（src/kabusys/__init__.py）
  - エクスポートモジュール: data, strategy, execution, monitoring を公開

- 環境設定・ロード機能を追加（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 詳細な .env パース実装（export プレフィックス、クォート文字とバックスラッシュエスケープ、インラインコメント取り扱い）
  - 必須環境変数チェック用 _require と Settings クラスを提供
    - 必須キー例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルト設定: KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（有効値のチェック）と環境判定ユーティリティ（is_live, is_paper, is_dev）

- AI（自然言語処理）モジュールを追加（src/kabusys/ai/）
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信
    - バッチサイズ・文字数・記事数制限（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - JSON Mode を前提としたレスポンス処理と堅牢なバリデーション（レスポンス整形・冗長テキスト抽出対応）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）
    - ルックアヘッドバイアス対策: target_date ベースのウィンドウ計算（calc_news_window）
    - テスト容易性を考慮し OpenAI 呼び出しの差し替えポイントを用意（_call_openai_api の patch を推奨）
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して
      日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む
    - MA 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）
    - マクロキーワードで raw_news をフィルタし LLM でマクロセンチメントを評価（記事がない場合は LLM 呼び出しをスキップ）
    - API エラー時は macro_sentiment=0.0 としてフェイルセーフに処理
    - OpenAI 呼び出しの独立実装によりモジュール間結合を抑制

- リサーチ用ファクター / 特徴量モジュールを追加（src/kabusys/research/）
  - ファクター計算 (factor_research)
    - calc_momentum: 約1/3/6か月のリターン、ma200 乖離（データ不足時は None）
    - calc_volatility: 20日 ATR、相対 ATR(atr_pct)、20日平均売買代金、出来高比率
    - calc_value: raw_financials から EPS/ROE を用いた PER, ROE の算出（target_date 以前の最新データを使用）
    - 設計方針: DuckDB 上の SQL を用いて計算、外部 API へはアクセスしない
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（有効レコード3未満で None）
    - rank: 平均ランク（同順位は平均ランク）を算出（丸めで ties 対応）
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算
  - research パッケージは主要関数を __all__ で公開（zscore_normalize は data.stats から再利用）

- データプラットフォーム関連モジュールを追加（src/kabusys/data/）
  - カレンダー管理 (calendar_management)
    - JPX カレンダー取得ジョブ（calendar_update_job）とマーケットカレンダーを利用した営業日判定ユーティリティ
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバック
    - market_calendar のデータ欠損や NULL 値に対するログと安全なフォールバックを実装
    - カレンダー取得時のバックフィル、健全性チェック（未来日付異常検出）
    - J-Quants クライアント（jquants_client）との連携ポイント
  - ETL パイプライン (pipeline)
    - ETLResult データクラスを提供（ETL の統計、品質問題、エラーを集約）
    - 差分取得・バックフィル・品質チェックを想定した設計（jquants_client, quality と連携）
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを提供
  - etl モジュールで ETLResult を再エクスポート（data.etl）

- パッケージ設計上の共通配慮
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を主要計算に直接利用しない設計（target_date を引数で明示）
  - DuckDB を前提としたクエリ実装と互換性配慮（executemany の空リスト回避等）
  - ロギングと警告メッセージにより不正・不足データ時の可観測性を確保
  - テスト容易性のため外部 API 呼び出し箇所に差し替えポイント（モック箇所）を用意

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの取得は引数優先 → 環境変数（OPENAI_API_KEY）フォールバックの明確化
- 環境変数の必須チェックを Settings で提供し、未設定時に明確なエラーメッセージを出力

Notes / Implementation details
- OpenAI モデル: gpt-4o-mini を利用する設計で、JSON Mode（response_format={"type":"json_object"}）を用いた堅牢なパースを行う
- API 呼び出し失敗時の挙動:
  - news_nlp: 失敗したチャンクはスキップして他チャンクを継続
  - regime_detector: マクロセンチメントが取得できない場合は 0.0 にフォールバック
- DuckDB を前提に SQL を組み立てているため、DB スキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials など）に依存する
- 一部ユーティリティ関数は公開されておらず内部用（_call_openai_api 等）。テストでは unittest.mock.patch による差し替えを想定

作者
- (このCHANGELOGはコードベースの内容から自動的に推測して作成しています)