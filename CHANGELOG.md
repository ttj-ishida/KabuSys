# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

現行バージョン: 0.1.0

## [0.1.0] - 2026-03-28

最初の公開リリース。本バージョンで導入された主な機能・モジュールは以下の通りです。

### 追加
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - __all__ に data, strategy, execution, monitoring を公開対象として定義。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - .env 解析器: コメント、export プレフィックス、シングル/ダブルクォートとエスケープに対応。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 必須環境変数チェック用の _require ユーティリティと各種プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証、is_live/is_paper/is_dev の便宜プロパティ。
  - デフォルト DB パス (duckdb/sqlite) の拡張処理 (expanduser)。

- AI モジュール (kabusys.ai)
  - news_nlp（ニュースのセンチメント計算）と regime_detector（市場レジーム判定）を提供。
  - OpenAI（gpt-4o-mini）を用いた JSON-mode 呼び出しを採用。
  - API 呼び出しは再試行（指数バックオフ）、429/ネットワーク断/タイムアウト/5xx に対応。
  - フェイルセーフ処理: API 失敗時は例外を投げず安全側の既定値（news -> 0.0 / regime -> macro_sentiment=0.0）で継続。
  - テスト容易性のため API 呼び出し箇所は内部関数化しモック差し替え可能（unittest.mock.patch を想定）。
  - score_news: raw_news と news_symbols を集約して銘柄ごとにスコアを取得、ai_scores テーブルへ冪等的に保存（DELETE → INSERT）。
    - バッチ処理（最大 20 銘柄／回）、1銘柄あたりの記事数と文字数トリム制御あり。
    - レスポンスバリデーション（JSON 抽出、results 配列、code/score 検証）を実施。
    - DuckDB 0.10 互換性対応（executemany に空リストを渡さない等）。
  - score_regime: ETF 1321 の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成し market_regime テーブルへ書き込み。
    - マクロ記事抽出はキーワードベース、記事が無ければ LLM 呼び出しをスキップ。
    - レジームスコアの閾値で bull / neutral / bear を判定。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。失敗時は ROLLBACK。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX カレンダー（market_calendar）に基づく営業日判定ユーティリティを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB にデータがない場合は土日フォールバックで判定。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やカレンダー先読み、バックフィル、健全性チェックを実装。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得し保存する夜間ジョブ。バックフィルと安全チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。ETL 実行結果の集約、品質検査結果・エラーの列挙を保持。
    - 差分更新、保存（idempotent）、品質チェックの方針とユーティリティ関数を実装（_get_max_date 等）。
    - J-Quants の初回ロード日やバックフィル等の定数を定義。
  - jquants_client を参照する実装（fetch/save 関数は別モジュール想定）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均出来高・売買代金）、
      バリュー（PER, ROE）などの計算関数を実装。
    - DuckDB を用いた SQL+Python 実装で、prices_daily / raw_financials を参照。
    - データ不足時の None ハンドリングやログ出力を実装。
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns): 任意ホライズン（デフォルト [1,5,21]）で LEAD を用いて一括取得。
    - IC（calc_ic）: factor と将来リターン間のスピアマンランク相関を計算（同順位は平均ランクで処理）。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を算出（None 除外）。
    - rank ユーティリティ: 値→ランク変換（同順位は平均ランク、丸め対策あり）。
  - data.stats からの zscore_normalize を再エクスポート（kabusys.research.__init__）。

### 変更（設計上の決定・振る舞い）
- ルックアヘッドバイアス防止
  - AI 統計や ETL / リサーチ側の関数は datetime.today()/date.today() を内部で参照せず、明示的な target_date 引数で動作する設計を採用。
  - news / regime などの DB クエリは target_date 未満または指定ウィンドウの排他条件を用いてルックアヘッドを防止。

- OpenAI 呼び出し
  - JSON mode を使い厳密 JSON 出力を期待する（応答パースの保険として前後テキスト抽出処理あり）。
  - エラーの種類に応じた再試行戦略とログ出力、最終的には安全値でフォールバックする挙動を採用。

- DuckDB 互換性
  - DuckDB 0.10 の挙動（executemany に空リスト不可、配列バインドの不安定さ）を考慮して実装。

### 修正（バグフィックス等）
- 初版リリースのため既知のバグ修正履歴はなし（初期実装）。

### セキュリティ
- API キーは関数引数で注入可能（テストや鍵管理の柔軟性向上）。環境変数（OPENAI_API_KEY 等）も利用可。
- .env 自動ロード機能はテスト用に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### 既知の注意点 / 制約
- DuckDB 接続を前提とする。テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）のスキーマが必要。
- OpenAI (gpt-4o-mini) 利用のため適切な API キーと利用制限への対応が必要。
- ETL / calendar_update_job は jquants_client の実装に依存する（fetch/save 関数が必要）。
- JSON-mode での LLM 応答に対する堅牢化（パース失敗時はスキップ/0.0 フォールバック）を行っているが、LLM 出力仕様の変化に影響される可能性あり。

---

今後のリリースでは以下を検討しています（非確定）:
- パフォーマンス改善（大規模データのバッチ処理最適化）
- より厳密な型チェック・型ヒント拡張
- CLI / 管理用コマンドの追加
- テストカバレッジ拡張と CI 統合

（この CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴と差異がある場合があります。）