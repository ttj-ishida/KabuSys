# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

## [0.1.0] - 2026-04-01
初回リリース

### 追加
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ公開インターフェース: data, strategy, execution, monitoring（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数 / .env ファイル読み込みユーティリティを追加（src/kabusys/config.py）。
    - プロジェクトルート判定（.git または pyproject.toml を探索）により CWD に依存しない自動ロード実装。
    - .env / .env.local の読み込み順序を実装（.env.local が上書き、OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパース機能を充実:
      - コメント行・空行無視、export プレフィックス対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
      - インラインコメントの扱い（クォート外で直前が空白/タブの `#` をコメントとみなす）。
    - Settings クラスを提供。主なプロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH
      - CPU/MEMORY/DISK 閾値（%）
      - KABUSYS_ENV（development / paper_trading / live のバリデーション）
      - LOG_LEVEL（DEBUG/INFO/... のバリデーション）
      - is_live / is_paper / is_dev フラグ

- AI（NLP）機能
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルを参照し、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini、JSON mode）へバッチ送信。
    - バッチサイズ、1銘柄あたりの最大記事数・最大文字数によるトリム制御。
    - 再試行（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフ実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score の検証）。
    - スコアは ±1.0 にクリップ。
    - DB への書き込みは冪等（DELETE → INSERT）で、部分失敗時に既存スコアの保護を行う。
    - テスト容易性のため _call_openai_api を patch 可能に実装。
    - 公開 API: score_news(conn, target_date, api_key=None)、calc_news_window(target_date)。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しに対する堅牢なリトライと 5xx 判定、失敗時はフェイルセーフで macro_sentiment=0.0 を使用。
    - DuckDB への書き込みはトランザクションで冪等（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK を試行。
    - 公開 API: score_regime(conn, target_date, api_key=None)。

- データプラットフォーム機能
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを使った営業日判定 API を提供:
      - is_trading_day(conn, d)
      - is_sq_day(conn, d)
      - next_trading_day(conn, d)
      - prev_trading_day(conn, d)
      - get_trading_days(conn, start, end)
    - DB 登録がない場合は曜日ベースのフォールバック（土日非営業）を使用し、DB とフォールバックで一貫した挙動をする設計。
    - 夜間バッチ: calendar_update_job(conn, lookahead_days) により J-Quants から差分取得し保存（バックフィルと健全性チェック実装）。
    - 最大探索範囲やバックフィル、健全性（将来日付過大）チェックを実装。

  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを追加（ETL の取得件数／保存件数／品質問題／エラーの集約）。
    - 差分取得、保存（jquants_client 経由の冪等保存）、品質チェック（quality モジュール連携）を想定した設計。
    - デフォルトのバックフィル日数、カレンダーの先読み等の定数を定義。
    - etl モジュールでは ETLResult を公開インターフェースとして再エクスポート。

- リサーチ / ファクター解析機能（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、流動性指標（20日平均売買代金、出来高比）を計算する関数:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)（raw_financials と prices_daily を組み合わせて PER・ROE を算出）
    - DuckDB を用いた SQL ベース計算（外部 API にアクセスしない設計）。
    - データ不足時は None を返す扱い。
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons)
    - IC（Information Coefficient）計算 calc_ic(...)
    - ランク化ユーティリティ rank(values)
    - 統計サマリー factor_summary(records, columns)
  - research パッケージの __all__ による公開関数の整理。

### 設計上の重要な注意点 / 制約
- ルックアヘッドバイアス防止:
  - 各モジュール（AI スコア、レジーム判定、ファクター計算、ニュースウィンドウ等）は内部で datetime.today()/date.today() を参照せず、呼び出し側から target_date を受け取る設計。
- OpenAI 連携:
  - API キーは関数引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY を参照。
  - API キー未設定時は ValueError を送出（明示的なエラー）。
- フェイルセーフ:
  - LLM / API 呼び出しの失敗は例外ではなくフォールバック（例: スコア 0.0、該当チャンクスキップ）で継続する箇所が多い（運用継続性重視）。
- DuckDB 互換性:
  - executemany の空リストバインドや配列バインドの不整合を考慮した実装（空チェックや個別 DELETE 実行など）。
- テストフック:
  - OpenAI 呼び出し用の内部関数はパッチ可能に実装されており、ユニットテストで容易にスタブ化可能。

### 既知の制限 / TODO（将来改善候補）
- 一部外部クライアント（jquants_client）の実装は本リリースのコードベースから参照されるが、実体は別モジュール / パッケージに依存。
- PBR・配当利回りなどのバリュー指標は現バージョンでは未実装（calc_value の注記）。
- news_nlp / regime_detector は gpt-4o-mini の JSON mode に依存するため、API の将来的な仕様変更に注意が必要。
- エラーハンドリング、監査ログ、メトリクス出力の拡充は今後の改善点。

---

今後のリリースでは、バグ修正・テストカバレッジの拡充・追加ファクター実装・運用モニタリング統合などを予定しています。