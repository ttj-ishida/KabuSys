# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはリポジトリ内の公開 API と主要機能（コードベース）から推測して作成した初期リリースの変更履歴です。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各バージョン: 追加・変更・修正点を列挙

## [Unreleased]
（今後の変更をここに記載）

---

## [0.1.0] - 2026-03-31
初回公開リリース

### Added
- パッケージの基本構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - パッケージは少なくとも次のサブパッケージを公開: data, strategy, execution, monitoring（strategy/execution/monitoring は将来的なエントリポイントとして __all__ に含む）

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込みを実装（プロジェクトルート判定: .git または pyproject.toml を基準）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化可能
  - .env パーサーを独自実装（export 文対応、クォート内部のバックスラッシュエスケープ、インラインコメント処理）
  - override / protected をサポートする .env ロード（OS 環境変数保護）
  - Settings クラスを提供（settings オブジェクトをエクスポート）
    - J-Quants、kabuステーション、Slack などの必須/任意設定をプロパティ経由で取得
    - デフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等）を設定
    - 環境変数バリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）
    - ヘルプ的なエラーメッセージを備えた必須値チェック (_require)

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP: score_news (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄別センチメント（-1.0〜1.0）を算出
    - バッチ処理（最大 20 銘柄／リクエスト）とトークン肥大化対策（1銘柄当たり最大記事数・文字数制限）
    - 再試行（429, ネットワーク断, タイムアウト, 5xx は指数バックオフでリトライ）、それ以外はフェイルセーフによりスキップ
    - レスポンスバリデーション（JSON 抽出、results フォーマット検証、未知コード無視、数値検査、±1.0でクリップ）
    - DuckDB への冪等的書き込み（DELETE → INSERT、部分失敗に備えコードを絞って更新）
    - テスト容易性: _call_openai_api のモック差し替えが可能
    - calc_news_window 関数を提供（target_date に対するニュース収集ウィンドウの厳密な算出。JST→UTC の扱いに注意）

  - 市場レジーム判定: score_regime (src/kabusys/ai/regime_detector.py)
    - ETF (1321) の 200 日移動平均乖離（重み 70％）とマクロニュース LLM センチメント（重み 30％）を合成して日次レジーム（bull/neutral/bear）を算出
    - prices_daily からの MA 計算でルックアヘッドを防止（target_date 未満のみ使用）
    - マクロ記事は raw_news からキーワードで抽出して OpenAI に投げる（最大記事数制限）
    - OpenAI 呼び出しはリトライ・5xx 判定・フェイルセーフ（失敗時 macro_sentiment = 0.0）
    - レジームスコアのクリップと閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - テスト容易性: _call_openai_api は差し替え可能

- Data モジュール (src/kabusys/data/)
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを提供（取得/保存件数、品質問題、エラーを集約）
    - 差分更新、バックフィル戦略、品質チェックの設計方針を実装（J-Quants クライアントと連携）
    - DuckDB のテーブル存在チェック、最大日付取得等のユーティリティ
    - ETLResult.to_dict() で品質問題を辞書化して出力可能

  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を扱うユーティリティ群
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動
    - 夜間バッチ更新 job: calendar_update_job（J-Quants から差分取得・保存、バックフィル、健全性チェック）
    - 最大探索日数やバックフィル、ルックアヘッド日数等の安全策を導入

  - ETL インターフェース公開（src/kabusys/data/etl.py）
    - pipeline.ETLResult を再エクスポート

- Research モジュール (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: モメンタム系 (1M/3M/6M) と 200 日 MA 乖離を計算。データ不足は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算。欠損は None。
    - calc_value: raw_financials と prices_daily を組み合わせ PER/ROE を算出（EPS=0 等は None）。
    - DuckDB のウィンドウ関数等を活用した実装。外部 API 呼び出しなし。

  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（営業日）後の将来リターンを取得（デフォルト [1,5,21]）
    - calc_ic: スピアマンランク相関（IC）を計算。レコード不足（<3）で None を返す
    - rank: 同順位は平均ランクにするランク関数（丸め処理で ties 判定の安定化）
    - factor_summary: count/mean/std/min/max/median の統計サマリー計算
    - zscore_normalize は kabusys.data.stats から再エクスポート（research パッケージ経由）

### Design / Implementation Notes
- ルックアヘッドバイアス防止
  - AI モジュールやリサーチ関数は datetime.today() / date.today() を内部で参照せず、明示的に target_date を受け取る設計。
  - DB クエリは target_date の未満/未満等の排他条件を厳守。

- 冪等性・障害耐性
  - DB 書き込みは可能な限り冪等（DELETE→INSERT や ON CONFLICT 想定）で実装。
  - OpenAI など外部 API 呼び出しはリトライとフェイルセーフ（失敗時 0.0 やスキップ）で継続する設計。

- テスト容易性
  - OpenAI 呼び出し部分はモジュール内の private 関数（_call_openai_api）を unittest.mock.patch で置き換えられるように実装。

- DuckDB 互換性
  - executemany に空リストを渡せない制約（DuckDB 0.10）に配慮し、空チェックを行っている箇所あり。

### Security / Requirements
- 外部サービスの API キーは環境変数経由で期待:
  - OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など
- OpenAI 連携は gpt-4o-mini を使用（JSON mode を利用）
- DuckDB を想定したデータベーススキーマ（prices_daily, raw_news, raw_financials, ai_scores, market_regime, market_calendar 等）が前提
- .env 自動ロードはプロジェクトルート探索に .git / pyproject.toml を使用するため、配布・運用環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を推奨（テストや CI の場合）

### Known limitations / TODO（推測）
- strategy / execution / monitoring サブパッケージは __all__ に含まれているが、本差分に該当する実装ファイルが提示されていない（今後追加予定）。
- 一部ユーティリティ（例: kabusys.data.stats モジュール）は再エクスポートされているが、コード一覧に含まれていないため依存関係の確認が必要。

---

メンテナ向け補足:
- この CHANGELOG はコードからの推測に基づいて作成しています。実際のリリースノートとして公開する前に、変更内容・バージョン番号・日付・依存関係をリポジトリの実際の履歴やリリース方針と照合してください。