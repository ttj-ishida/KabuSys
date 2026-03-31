Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

- （現時点のリリースは v0.1.0 のため未リリース項目はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ公開情報:
    - src/kabusys/__init__.py: __version__ = "0.1.0"
    - パブリックサブパッケージとして data, strategy, execution, monitoring を想定。

- 設定管理:
  - src/kabusys/config.py
    - Settings クラスを通じて環境変数ベースの設定を提供（settings インスタンス）。
    - 必須変数取得用の _require() を実装（未設定時は ValueError を送出）。
    - .env 自動読み込み機能:
      - プロジェクトルートは .git または pyproject.toml を基準に探索（_find_project_root）。
      - 読み込み順序: OS 環境変数 > .env.local > .env。.env.local は上書き（override=True）。
      - OS 環境変数を保護する protected キー群を導入（既存値の上書き防止）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化可能。
    - .env パーサは export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
    - 許容値チェック: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証。

- AI（ニュース NLP / レジーム判定）:
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ保存するフローを実装。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() で計算。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたり記事数・文字数の上限（トリム）を設定（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - API 呼び出しのリトライ／エクスポネンシャルバックオフ実装（429、ネットワーク断、タイムアウト、5xx が対象）。
    - レスポンスの厳格なバリデーション（JSON 抽出、results キー、コード整合性、数値チェック）、スコアは ±1.0 にクリップ。
    - DuckDB への書き込みは冪等性を考慮（DELETE→INSERT、executemany の空リスト回避）。
    - フェイルセーフ: API エラーやパース失敗時は該当チャンクをスキップし、例外を全体に拡げない設計。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のみ使用）、マクロ記事抽出（キーワードによるフィルタ）を実装。
    - OpenAI 呼び出し（gpt-4o-mini、JSON mode）とリトライ戦略、API 失敗時の macro_sentiment=0.0 フォールバック。
    - レジームスコア合成、閾値に基づくラベリング、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1 を返す（成功時）。

  - 実装方針共通:
    - OpenAI 呼び出しはモジュール間で private な呼び出し関数を共有せず各モジュール内に実装（テストで差し替え可能）。
    - レスポンスは JSON のみを期待するプロンプトを採用し、余分なテキスト混入に対する復旧ロジックを含む。
    - いずれの処理も date/datetime の現在参照（datetime.today() / date.today()）を避け、ルックアヘッドバイアスを抑制。

- データプラットフォーム:
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理機能を提供（market_calendar テーブル）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の営業日判定ユーティリティを実装。
    - カレンダーデータが存在しない場合は曜日ベースのフォールバック（平日を営業日）を採用。
    - 夜間バッチ更新 calendar_update_job(conn, lookahead_days=90) で J-Quants API から差分取得し DB へ冪等保存。バックフィル、健全性チェック（未来日異常検知）を実装。
    - DB の値を優先しつつ未登録日は曜日フォールバックで一貫した振る舞いを保つ。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの基本構造とユーティリティを実装。
    - ETLResult データクラスを定義（取得数／保存数／品質問題／エラー一覧等を保持）。
    - 差分更新・バックフィル戦略、品質チェック（quality モジュールを利用）を想定。
    - DuckDB に対するテーブル存在チェックや最大日付取得ユーティリティを実装。
    - src/kabusys/data/etl.py では ETLResult を再エクスポート。

- リサーチ（研究）モジュール:
  - src/kabusys/research/factor_research.py
    - モメンタム (1M/3M/6M)、200日 MA 乖離、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比）等を計算する関数群:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)（raw_financials から PER/ROE を計算）
    - DuckDB の SQL を主に用いて高速に集計する実装。データ不足時は None を返す等の設計。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンのランク相関。
    - ランキングユーティリティ rank(values)（同順位は平均ランク）。
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median を計算）。
    - 外部依存（pandas 等）を用いず標準ライブラリのみで実装。

- 実装上の注意点・設計判断（ドキュメント化された重要点）
  - ルックアヘッドバイアス対策: 日時の「現在参照」を避け、関数はすべて target_date を明示的に受け取る。
  - DuckDB 互換性: executemany に空リストを渡さないなどの互換性配慮。
  - DB 書き込みの冪等性を重視（DELETE→INSERT、ON CONFLICT の利用想定）。
  - OpenAI 呼び出しは各モジュールで分離して実装し、テストで差し替え可能にしている。
  - フェイルセーフ: 外部 API エラー時は可能な限り処理を継続し、致命的でない限りスキップしてログに記録。

Known issues / Notes
- Settings により多くの値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）が必須になっている。未設定時は ValueError が発生するため、実行前に .env を準備する必要あり。
- OpenAI API キーは score_news / score_regime の引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照する（必須）。
- strategy / execution / monitoring サブパッケージは __all__ に含まれるが、この差分に含まれるソース一覧では詳細な実装は示されていない（将来の追加想定）。

Authors
- kabusys 開発チーム（コードベースのソースコメントに基づきまとめました）。

---

（この CHANGELOG は提示されたソースコードを基に推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。）