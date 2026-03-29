Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

0.1.0 - 2026-03-29
-----------------

Added
- パッケージ基盤
  - kabusys パッケージ初期リリース。バージョンは 0.1.0。
  - モジュール公開: data, research, ai, execution, monitoring 等を __all__ で定義（execution / monitoring はプレースホルダ含む）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定をロードするユーティリティを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を起点に探索し、配布後も CWD に依存しないよう設計。
  - .env のパース実装: export プレフィックス、クォート、エスケープ、インラインコメント処理に対応。
  - 自動ロード順序: OS 環境 > .env.local (override) > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / 環境種別・ログレベルの取得とバリデーションを実装。
  - 必須変数未設定時は ValueError を送出する _require を用意。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄ごとにテキストを生成し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメント評価を行い ai_scores テーブルに書き込む機能を実装（score_news）。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して対象抽出（calc_news_window）。
  - バッチ処理: 1 API 呼び出しで最大 20 銘柄（_BATCH_SIZE）を処理。1 銘柄あたりの最大記事数・最大文字数でトリム。
  - 再試行ロジック: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
  - レスポンス検証: JSON 抽出、"results" の存在確認、code/score の検証、スコアを ±1.0 にクリップ。
  - 部分成功時の DB 書き換え戦略: 取得済みコードのみ DELETE → INSERT（部分失敗で既存データを保護）。
  - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の直近 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定（score_regime）。
  - MA 計算は target_date 未満のデータのみ使用してルックアヘッドバイアスを排除。
  - マクロニュースは raw_news からマクロキーワードで抽出し、LLM により -1.0～1.0 のスコア化を実施。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
  - OpenAI 呼び出しに対するリトライとエラー種別ハンドリングを実装。
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を利用した営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベース（平日）でフォールバックする設計。
    - calendar_update_job: J-Quants から差分取得し market_calendar を冪等保存。バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを実装し ETL 実行結果を構造化して返却。
    - 差分取得・バックフィル・品質チェックの設計方針を実装に反映（_jquants_client 連携箇所は jquants_client を利用）。
    - DuckDB 上での最大日付取得ユーティリティやテーブル存在チェック等を提供。
  - etl.py で ETLResult を再エクスポート。

- Research（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比等を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0/欠損 の場合 PER は None）。
    - いずれも DuckDB の SQL ウィンドウ関数を活用して performant に実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括で取得（複数ホライズンを同時に処理）。
    - calc_ic: スピアマンのランク相関（IC）を実装（結合・None 削除・最小サンプル数チェック含む）。
    - rank, factor_summary: ランク化（同順位は平均ランク）と基本統計量算出を提供。
  - 設計全体で「datetime.today()/date.today() を参照しない」方針を徹底し、ルックアヘッドバイアスを防止。

- テスト・運用配慮
  - OpenAI 呼び出しや環境ロードをテストで差し替え可能なポイントを用意（関数分離・注入可能）。
  - DuckDB 0.10 の制約（executemany に空リストを渡せない）に対するワークアラウンドを実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初期設計段階での堅牢性向上:
  - OpenAI API 呼び出し時の各種例外（RateLimit, Timeout, ConnectionError, APIError）を個別にハンドリングしリトライ/フォールバックを実装。
  - DB 書き込みでの ROLLBACK 保護、ROLLBACK 失敗時の警告ログ出力。

Removed
- 初回リリースのため該当なし。

Security
- API キー等のシークレットはコードに埋め込まず環境変数で取得。OpenAI API キー未設定時は ValueError を発生させ早期検出。
- 自動 .env ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。

Known issues / Notes
- OpenAI へのプロンプトは厳密な JSON の返却を期待しているが、実運用では LLM の出力が崩れることがあるため、JSON 抽出や復元ロジックを導入している（それでも完全ではないためログに注意）。
- 一部のテーブル・クライアント（例: jquants_client）の実装はこのコードベース外に依存しているため、実行前に外部クライアントの設定が必要。
- calc_value では現時点で PBR・配当利回りなどは未実装。
- score_news / score_regime は OpenAI モデル（gpt-4o-mini）を利用するため利用量とレート制限に注意が必要。
- raw_news.datetime は UTC 保存を想定しているため、データ供給側は UTC に統一すること。

開発上の注記
- ルックアヘッドバイアス回避のため、スコアリング処理は target_date 引数に基づいて過去データのみ参照する設計になっています。バッチ実行やバックテストでの使用に適しています。
- DuckDB を用いた設計で SQL のウィンドウ関数を多用しています。パフォーマンスチューニングは今後の課題です。

今後の予定（例）
- PBR・配当利回りなどバリューファクターの追加実装。
- モデル選択やプロンプト改善による NLP 品質向上。
- ETL の監視 / 再試行メカニズムの拡充。
- 単体テストおよび統合テストの整備（外部 API モックの標準化）。

-----