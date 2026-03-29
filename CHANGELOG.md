CHANGELOG
=========

すべての注目すべき変更を、Keep a Changelog の仕様に準拠して日本語で記載します。  

フォーマット:
- Added: 新機能
- Changed: 変更
- Fixed: 修正
- Removed / Deprecated / Security: 該当があれば記載

なお、本リリースはパッケージバージョン 0.1.0（src/kabusys/__init__.py の __version__）に対応します。

Unreleased
----------

（現在のリポジトリ状態が初回リリース相当のため、Unreleased の項目はありません。）

0.1.0 - 2026-03-29
------------------

Added
- 基本情報
  - パッケージ初期リリース。バージョンは 0.1.0。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 行の高度なパーシング:
    - export KEY=val 形式対応
    - シングル/ダブルクォートのエスケープ処理対応
    - インラインコメントの扱い（クォートの有無に応じた振る舞い）
  - OS 環境変数を保護する protected オプションと override ロジック。
  - 必須変数チェック用の _require()、および J-Quants / kabu / Slack / DB パス等のプロパティを実装。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - calc_news_window(target_date) によるニュース収集ウィンドウ計算（JST → UTC 換算）。
    - score_news(conn, target_date, api_key=None)：raw_news / news_symbols を集約し OpenAI（gpt-4o-mini / JSON mode）で銘柄ごとのセンチメントを算出、ai_scores テーブルへ冪等書き込み。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたりの記事数や文字数トリム設定を搭載。
    - API 呼び出し失敗（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score の検証）とスコアの ±1.0 クリップ。
    - DuckDB 互換性対策（executemany に空リストを渡さない等）。
    - テスト容易性のため _call_openai_api をパッチできる実装。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - score_regime(conn, target_date, api_key=None)：ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込み。
    - _calc_ma200_ratio によるルックアヘッド防止（target_date 未満のデータのみ使用）とデータ不足時のフォールバック（中立 1.0）。
    - マクロニュース取得（news_nlp.calc_news_window を利用）と OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価。API 失敗時はフェイルセーフで 0.0 を使用。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と適切なエラーハンドリング／ROLLBACK。

- データプラットフォーム / ETL (src/kabusys/data)
  - calendar_management.py
    - JPX マーケットカレンダー管理 API を想定した機能群:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得の際の曜日ベースフォールバック（週末は非営業日）を実装。
    - 最大探索範囲（_MAX_SEARCH_DAYS）や先読み・バックフィル・健全性チェックを含む calendar_update_job により J-Quants クライアント経由でカレンダーを取得・保存。
    - DB 登録値優先／未登録日は曜日フォールバックの一貫した扱い。

  - pipeline.py / etl.py
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧などを格納）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を想定した設計。
    - _get_max_date 等のユーティリティを実装。
    - etl.py で ETLResult を再エクスポート。

- Research（解析） (src/kabusys/research)
  - factor_research.py
    - calc_momentum(conn, target_date)：mom_1m / mom_3m / mom_6m / ma200_dev を計算。
    - calc_volatility(conn, target_date)：ATR20、相対 ATR（atr_pct）、平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date)：raw_financials から EPS/ROE を取得し PER/ROE を計算（未実装の指標も注記）。
    - DuckDB SQL を利用し、prices_daily / raw_financials のみ参照する安全な実装。
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons)：複数ホライズンの将来リターンを一括で取得（ホライズンのバリデーションあり）。
    - calc_ic(factor_records, forward_records, ...)：スピアマンランク相関（IC）を実装（同順位は平均ランクで処理）。
    - rank, factor_summary：ランク付けロジックと統計サマリーを提供。
    - pandas 等の外部ライブラリに依存しない実装方針。

- その他
  - 各モジュールで「ルックアヘッドバイアス防止」の設計方針を明記（datetime.today()／date.today() を直接参照しない等）。
  - OpenAI クライアント呼び出し箇所はテスト用に差し替え可能な設計（ユニットテスト想定）。
  - DuckDB の挙動差異（list バインド／executemany の空リスト等）に対する互換性対応をコード中に組み込み。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Security
- 初回リリースにつき該当なし。ただし機密情報の取り扱いに関して:
  - 環境変数の読み込みは .env を用いる設計で、OS 環境変数を保護するための protected 機能を提供。
  - OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決するが、ログ出力等での露出は行わない実装方針。

Deprecated / Removed
- 初回リリースにつき該当なし。

補足メモ（設計上の注意点）
- 多くの処理で「部分失敗時に他データを保護する」ため、DB 書き込みは対象コードを絞った DELETE → INSERT のような局所的置換を採用しています（ai_scores、market_regime 等）。
- AI 呼び出しは外部サービス依存のため、ネットワーク問題やレート制限に耐えるリトライ・フォールバックロジックを備えています。API 失敗時はゼロ値（中立）で継続するなどフェイルセーフな設計です。
- テスト容易性を考慮し、外部 API 呼び出しをテスト時にモックできる構造にしています（例: unittest.mock.patch で _call_openai_api を差し替え可能）。

今後の予定（参考）
- ai スコアリングのスキーマ拡張（PBR・配当利回りなどのバリュー指標拡張）
- モデルやプロンプトの継続的改善および追加テストカバレッジ
- データ品質チェック（quality モジュール）の強化と通知（監視）統合

以上。