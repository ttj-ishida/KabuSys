CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

（現時点では未リリースの差分はありません）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開用メタ情報: src/kabusys/__init__.py（__version__ = "0.1.0", __all__ の定義）。
- 環境設定管理モジュール (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションを追加（テスト向け）。
  - .env パーサ実装: export プレフィックス対応、引用符付き値内のバックスラッシュエスケープ処理、インラインコメントの取り扱いを実装。
  - .env.local が .env を上書きする優先度ルールを実装。OS 環境変数は protected として上書き抑止。
  - Settings クラスを提供し、環境変数からの値取得をプロパティ化:
    - J-Quants / kabu ステーション / Slack / DB パス等の設定をプロパティ経由で取得。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）を実装。
    - duckdb/sqlite のデフォルトパス設定（data/...）を提供。
    - is_live / is_paper / is_dev ヘルパーを追加。
- AI モジュール: ニュース NLP と市場レジーム判定 (src/kabusys/ai/)
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI (gpt-4o-mini) にバッチ送信してセンチメントを算出。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST → UTC 変換）を実装。
    - 1 バッチ最大 20 銘柄、1 銘柄あたり最大 10 記事・3000 文字でトリムするトークン肥大化対策。
    - JSON mode のレスポンス検証と復元（前後の余計なテキストを含む場合は最外側の {} を抽出）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ実装。その他エラーはスキップしてフェイルセーフに継続。
    - スコアを ±1.0 にクリップ。取得したスコアのみ ai_scores テーブルへ DELETE → INSERT で冪等的に書込み。
    - テスト容易性のため _call_openai_api をモック差替え可能に設計。
  - regime_detector.score_regime
    - ETF 1321（225 連動型）の直近 200 日終値からの MA200 乖離を計算（look-ahead 回避のため target_date 未満のみ利用）。
    - マクロニュース（マクロキーワードでフィルタ）を LLM でセンチメント評価し、MA（重み 70%）とマクロ（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しのリトライ、API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ。
    - 結果を market_regime テーブルへ冪等書込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - テスト用に OpenAI 呼び出しを差替え可能（モジュール間の内部関数共有を避ける設計）。
- Research モジュール (src/kabusys/research/)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR, 相対 ATR (atr_pct), 20 日平均売買代金, 出来高比率を計算。NULL 管理・ウィンドウ要件を考慮。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS が無効な場合は None）。
    - DuckDB の window 関数を活用して SQL で効率的に計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード 3 件未満は None）。
    - rank / factor_summary: ランク付け（同順位は平均ランク処理）と列ごとの基本統計サマリーを提供。
  - research パッケージで data.stats.zscore_normalize を再エクスポートし、分析ワークフローをサポート。
- Data モジュール (src/kabusys/data/)
  - calendar_management:
    - market_calendar に基づく is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック。
    - calendar_update_job: J-Quants API から差分取得 → save_market_calendar で冪等保存、バックフィルや健全性チェック（将来日付異常時スキップ）を実装。
  - pipeline / etl:
    - ETLResult データクラスを提供（処理結果・品質チェック結果・エラーメッセージを格納、to_dict によりシリアライズ可能）。
    - 差分更新方針、backfill の説明と実装方針を反映（コード内に定数・ユーティリティを実装）。
  - jquants_client / quality 等の外部依存クライアントを利用する設計で、API 呼び出し部分は分離。
- 実装品質・運用面の配慮
  - すべての時間関連処理で datetime.today()/date.today() の無制限な参照を避け、ルックアヘッドバイアスを防止する設計方針を随所に反映。
  - DuckDB 0.10 の制約（executemany に空リスト不可など）を考慮した実装。
  - ロギングを適切に配置し、エラー時に例外を投げる箇所とフォールバックで無視する箇所を明確に分離。
  - OpenAI SDK のバージョン差分（APIError.status_code の有無など）に対して堅牢なエラーハンドリングを実装。

Changed
- 初回リリースのため "Changed" の履歴はなし。

Fixed
- 初回リリースのため "Fixed" の履歴はなし。

Deprecated
- なし。

Removed
- なし。

Security
- 外部 API キー（OpenAI 等）未設定時は明示的に ValueError を発生させるようにし、不意の無効な動作を防止。

Notes / 既知の制約
- OpenAI API を利用する機能は実行時に有効な OPENAI_API_KEY が必要。テスト時は api_key 引数で注入するか、各モック差替えを利用してください。
- DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が前提です。実行前にスキーマ準備が必要です。
- gpt-4o-mini を想定したプロンプト設計・JSON mode を利用しています。将来のモデル変更・API 仕様変更に伴う調整が必要になる可能性があります。

開発者向けメモ
- テスト容易性のため、OpenAI 呼び出しラッパー（_call_openai_api）をモックする想定で各所に設計上のフックを用意しています。
- 環境の自動読み込みロジックはプロジェクト内で .git または pyproject.toml を探してプロジェクトルートを決定します。パッケージ配布後の動作を意識した実装です。