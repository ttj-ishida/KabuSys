# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。日本株自動売買・データ基盤・リサーチ・AI ユーティリティ群をまとめた最初の機能セットを提供します。

### 追加 (Added)
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - 主要サブパッケージをエクスポート: data, research, ai, （および placeholder の strategy, execution, monitoring が __all__ に含まれる）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を提供（プロジェクトルートを .git または pyproject.toml から探索）。
  - 高度な .env パーサを実装:
    - コメント、export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメント取り扱いなどに対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
  - Settings クラスを実装し、アプリ設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / DB のパス（duckdb/sqlite）等の設定を取得。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）と LOG_LEVEL のバリデーション。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
  - 必須環境変数未設定時に明確な ValueError を投げる _require の導入。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 (news_nlp.score_news):
    - raw_news と news_symbols を使って銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
    - 1銘柄あたり最大記事数・文字数トリム、チャンク処理（最大 20 銘柄/コール）によりスケーラブルに対応。
    - レート制限・ネットワーク断・5xx に対するエクスポネンシャルバックオフリトライ。
    - レスポンス検証（JSON パース復元、"results" リスト・code/score の検証）を実装し、不正レスポンスはスキップ（例外を投げないフェイルセーフ）。
    - ai_scores テーブルへの冪等的書き込み（該当コードのみ DELETE → INSERT）で部分失敗時の既存データ保護。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - テスト容易性のため内部の OpenAI 呼び出しを差し替え可能（_call_openai_api を patch してモック化）。
  - 市場レジーム判定 (regime_detector.score_regime):
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成し、日次で market_regime を登録。
    - マクロ記事抽出は news_nlp の calc_news_window を利用し、マクロキーワードフィルタでタイトルを選定（最大 20 記事）。
    - OpenAI 呼び出しは JSON Mode を期待、再試行/バックオフを実装。API 失敗時は macro_sentiment = 0.0 として継続（フェイルセーフ）。
    - レジームスコア算出後、DB へ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。失敗時は ROLLBACK を試みて例外を上位に伝播。
    - ルックアヘッドバイアス対策として、target_date 未満のデータのみを参照（datetime.today()/date.today() を直接参照しない）。

- データ基盤・ETL (kabusys.data)
  - ETL インターフェース公開:
    - ETLResult データクラスを pipeline モジュールから再エクスポート（kabusys.data.etl.ETLResult）。
  - pipeline モジュール:
    - 差分取得・保存・品質チェック（quality モジュール）に基づく ETL の設計を実装する土台を用意。
    - ETLResult により ETL の結果や品質問題・エラー概要を構造化して返す。
    - DuckDB を前提とした最大日付取得等ユーティリティを提供。
  - カレンダー管理 (calendar_management):
    - JPX カレンダーの夜間更新 job（calendar_update_job）を実装: J-Quants から差分取得 → 市場カレンダーへ冪等保存。
    - 営業日判定ユーティリティを提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar 未取得時の曜日ベースフォールバック（週末を休日扱い）。DB 登録値優先で未登録日は曜日フォールバックし、一貫性を保つ設計。
    - バックフィル・健全性チェック（未来日付異常検出）・探索上限日数（_MAX_SEARCH_DAYS）を実装。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - Momentum: 約1/3/6ヶ月リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility / Liquidity: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等。
    - Value: PER（EPS が無効な場合は None）、ROE（raw_financials から最新値を取得）。
    - DuckDB のウィンドウ関数を利用し、date/code ベースで結果を返す。
    - データ不足時の None 処理・ログ出力。
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns): 指定ホライズンの将来終値比率を LEAD を使って一括取得。horizons のバリデーションあり。
    - IC 計算 (calc_ic): ファクター値と将来リターンのスピアマンランク相関を計算する実装。
    - rank ユーティリティ（同順位は平均ランク）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージは zscore_normalize（kabusys.data.stats）を含む複数 API を __all__ で公開。

### 変更 (Changed)
- 初版リリースのため過去バージョンからの変更はなし。すべて新規追加としてリリース。

### 修正 (Fixed)
- 初版リリースのため特定のバグ修正履歴は無し（実装段階でのフォールバック・ログ出力により堅牢性を確保）。

### セキュリティ (Security)
- OpenAI API キー取り扱い:
  - API キーは引数注入または環境変数 OPENAI_API_KEY から取得。未設定時は明示的に ValueError を発生させることで誤使用を防止。
- .env の自動読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

### 注意事項 / 設計上の重要点
- ルックアヘッドバイアス回避:
  - AI モジュール・リサーチモジュールは内部で datetime.today()/date.today() を参照せず、常に呼び出し側が指定する target_date に対して過去のデータのみを参照する設計になっています。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）呼び出しに失敗した場合、多くの箇所でスキップして処理を継続する（macro_sentiment=0.0 等）設計を採用し、部分失敗時にシステム全体が停止しないようにしています。
- テストしやすさ:
  - OpenAI 呼び出しの内部ラッパー関数（_call_openai_api）をモック可能にしており、ユニットテストで外部依存を差し替えやすくしています。
- DuckDB 前提:
  - データアクセスは DuckDB 接続を受け取る設計。SQL クエリは DuckDB の構文・制約（executemany の空リスト不可等）を考慮して実装されています。
- DB 書き込みは基本的に冪等化（DELETE → INSERT、ON CONFLICT 想定）されており、部分的な失敗で既存データを不用意に消さない配慮があります。

---

既知の未実装 / 今後のTODO（推測）
- Strategy / Execution / Monitoring パッケージは __all__ に含まれているが、このコードベース内での実実装は含まれていません（将来的な自動売買・注文実行・監視機能の追加想定）。
- PBR・配当利回りなどのバリューファクターは現バージョンでは未実装（calc_value に注記あり）。
- jquants_client / quality モジュールは参照されているが、実装の詳細や外部 API クライアントの仕様に対する調整が今後必要になる可能性があります。

（この CHANGELOG はソースコードのコメント・実装内容から推測して作成しています。リリースノートの正確な内容は実際のリリース方針に合わせて調整してください。）