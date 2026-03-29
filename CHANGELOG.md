# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

## [0.1.0] - 2026-03-29
初回公開リリース。

### 追加
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ公開用の __all__ を定義（data, strategy, execution, monitoring を想定）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込む（CWD に依存しない）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数保護のための protected 上書き制御を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途を想定）。
  - .env パーサーは以下をサポート:
    - 空行・コメント（#）の無視、先頭の "export " プレフィックスに対応
    - シングル/ダブルクォート付き値、バックスラッシュエスケープ対応
    - クォートなし値のインラインコメント処理（直前がスペース/タブの場合のみ）
  - Settings クラスを提供し、プロパティ経由で設定値を取得（必須項目の未設定時は ValueError を送出）。
  - デフォルト値や検証を導入:
    - KABUSYS_ENV の許容値: development / paper_trading / live（不正値は例外）
    - LOG_LEVEL の許容値: DEBUG/INFO/WARNING/ERROR/CRITICAL
    - データベースパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - Slack / Kabuステーション / J-Quants 等の必須トークン/パスワード取得プロパティを実装

- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp モジュールを追加:
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - ニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装（UTC 変換済み）。
    - バッチ処理（最大 20 銘柄ずつ）、1 銘柄あたり最大記事数・文字数でトリムする保護、JSON mode を使った厳密なレスポンス処理。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスのバリデーション（results リスト、code/score の型チェック、未知コードの無視、数値の有限性チェック）と ±1.0 のクリッピング。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）で冪等性を確保。DuckDB executemany の空引数問題に対応。
    - テスト容易化のため _call_openai_api を patch で差し替え可能。
  - regime_detector モジュールを追加:
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を判定。
    - MA 計算は target_date 未満のデータのみ使用してルックアヘッドバイアスを排除。データ不足時は中立（ma200_ratio=1.0）にフォールバック。
    - マクロニュース抽出はキーワードベースでタイトルを取得し、OpenAI（gpt-4o-mini）で macro_sentiment を JSON 出力で取得。API 失敗時は macro_sentiment=0.0 をフォールバック（例外を投げず継続）。
    - レジームスコア合成および bull/neutral/bear ラベル付与、DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）と ROLLBACK のハンドリング。
    - API 呼び出しに対してリトライ処理と 5xx 判定を実装、テスト差替え可能な設計。

- データ処理／ETL (kabusys.data)
  - pipeline モジュールを追加し、ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧などを保持）。
  - ETL 設計:
    - 差分更新・バックフィルの概念を導入（最終取得日から未取得範囲を自動計算、backfill 日数で後出し修正を吸収）。
    - jquants_client を介した冪等保存（ON CONFLICT DO UPDATE）との連携を想定。
    - 品質チェックを quality モジュールと連携し、重大度（severity）情報を集約して ETLResult に保持。
    - 内部ユーティリティとしてテーブル存在チェック、最大日付取得関数を実装。
  - etl モジュールで ETLResult を再エクスポート（外部利用向け）。
  - calendar_management モジュールを追加:
    - JPX 市場カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得のケースでは曜日ベース（土日を非営業日）でフォールバックする一貫した挙動を実装。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新、バックフィル・健全性チェック（極端な未来日付はスキップ）を実装。
    - 最大探索日数の上限を設定して無限ループを防止。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュールを実装:
    - モメンタム (calc_momentum): 1M/3M/6M リターンと 200 日 MA 乖離を計算。データ不足時は None を返す設計。
    - ボラティリティ/流動性 (calc_volatility): 20 日 ATR（true range を厳密に扱う）、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - バリュー (calc_value): raw_financials から直近財務データを取得して PER（EPS が 0/欠損なら None）と ROE を計算。
    - DuckDB 上の SQL で処理を完結させる設計（外部 API にアクセスせず本番口座への安全性を確保）。
  - feature_exploration モジュールを実装:
    - 将来リターン計算 (calc_forward_returns): 任意ホライズンの将来リターンを一度のクエリで取得。horizons の検証と上限（<=252）を実装。
    - IC（Information Coefficient）計算 (calc_ic): Spearman ランク相関を実装（同順位は平均ランク）。
    - rank ユーティリティ: 同順位の平均ランク処理、丸め誤差対策の round(v,12) を使用。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで実装。

### 設計上の注意点 / フェイルセーフ
- ルックアヘッドバイアス対策:
  - AI スコアリングやレジーム判定、ファクター計算等は内部で datetime.today()/date.today() を直接参照せず、引数の target_date に基づいて全てのウィンドウ計算を行う設計。
- 耐障害性:
  - OpenAI 呼び出しはリトライ・バックオフ・例外ハンドリングを実装し、API 失敗時はスコアを 0.0 やスキップで安全に継続するフェイルセーフを導入。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）と冪等化（DELETE→INSERT、ON CONFLICT 想定）で整合性を確保。
- テスト容易性:
  - OpenAI 呼び出しや内部 API 呼び出しを差し替え可能にしてユニットテストでのモックを容易にしている。
- DuckDB 互換性:
  - executemany の空リスト問題等、DuckDB の既知制約に配慮した実装（空時の処理分岐など）。

### 既知の未実装 / 今後の方針
- strategy / execution / monitoring パッケージの詳細実装はこのリリースでは含まれていない（__all__ に名前を用意）。
- 一部指標（例: PBR、配当利回り）は現フェーズでは未実装（calc_value に注記あり）。
- jquants_client / quality モジュールの具体的実装は別モジュールとして想定（calendar_management / pipeline から呼び出し）。

---

（今後の変更はこのファイルに逐次記録してください）