# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このプロジェクトのバージョンは src/kabusys/__init__.py の __version__ に同期しています。

すべての重要な変更・追加は日本語で記載しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買・研究プラットフォームのコア機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブモジュール公開: data, research, ai, execution, strategy, monitoring（__all__ にてエクスポート）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）を導入し、CWD に依存しない自動ロードを実現。
  - .env パーサーは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式
    - シングル/ダブルクォート付き値とバックスラッシュエスケープ
    - インラインコメント処理（クォート有りは無視、クォート無しは直前に空白がある # をコメントとみなす）
  - 自動ロード順序: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロード無効化可能（テスト用）。
  - protected（OS 環境変数の保護）を考慮した上書き制御。
  - Settings クラスを提供し、必要な設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_TOKEN 等）をプロパティで取得。環境値チェック（KABUSYS_ENV, LOG_LEVEL のバリデーション）を実装。

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI (gpt-4o-mini, JSON mode) にバッチ送信してセンチメントを ai_scores テーブルへ書き込み。
    - 処理ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTCで前日 06:00 〜 23:30 に変換）を計算する calc_news_window 実装。
    - バッチサイズ、最大記事数、トークン肥大化対策（最大文字数トリム）、JSON レスポンスの厳密バリデーションを実装。
    - 429 / ネットワーク切断 / タイムアウト / 5xx サーバエラーに対する指数バックオフのリトライ実装。
    - エラー時は例外を投げず（フェイルセーフ）、失敗チャンクはスキップ。最終的に取得できた銘柄のみ ai_scores を置換（DELETE→INSERT）することで部分失敗時に既存データを保護。
    - テスト容易性のため、内部の OpenAI 呼び出しは _call_openai_api をパッチ可能に実装。
    - DuckDB executemany の互換性（空リスト不可）に配慮。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とニュースの LLM センチメント（重み30%）を合成して当日の市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等書き込み。
    - LLM 評価は gpt-4o-mini、JSON mode を使用。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - ルックアヘッドバイアス回避: date 引数ベースで過去データのみ参照（datetime.today() 参照不可）。
    - 直近200日データ不足時のフォールバック動作と警告ログ。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを用いた営業日判定 API を実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - カレンダー夜間バッチ update_job を実装（J-Quants クライアント経由で差分取得→保存、バックフィル、健全性チェック）。
    - 最大探索日数や見通し日数などの安全措置を実装。

  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを導入して ETL 実行結果を構造化（取得数・保存数・品質チェック問題・エラー一覧を含む）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を前提とした設計。J-Quants クライアント（jquants_client）による保存処理を想定。
    - テーブル存在チェックや最大日付取得ユーティリティを実装。

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算 (research.factor_research)
    - モメンタム: 約1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を calc_momentum で実装。
    - ボラティリティ / 流動性: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率を calc_volatility で実装。
    - バリュー: raw_financials と prices_daily を結合し PER, ROE を calc_value で実装。
    - DuckDB を用いた SQL ベースの実装で、外部 API・注文系へのアクセスは一切行わない。

  - 特徴量探索 (research.feature_exploration)
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、horizons チェックあり）。
    - IC（Information Coefficient）計算 calc_ic（Spearman のランク相関）。
    - ランク変換ユーティリティ rank（同順位は平均ランク処理、丸めで ties を扱う）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
    - 研究用ユーティリティ群を一括エクスポート。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 (Notes)
- OpenAI API
  - gpt-4o-mini を想定しており、JSON mode を利用するプロンプト設計になっています。OpenAI SDK のバージョン差異により例外クラスや属性名が変わる可能性があるため、APIエラー処理は将来の変化にある程度耐性を持たせています。
  - API キーは関数引数（api_key）で注入可能。引数未指定時は環境変数 OPENAI_API_KEY を使用します。未設定時は ValueError を送出します。

- フェイルセーフ挙動
  - ネットワーク/API エラー時は多くの箇所でフェイルセーフ（0.0 でのフォールバック、あるいはチャンク単位でのスキップ）を採用しており、致命的ではない限り処理を継続します。ただし最終的な書き込み失敗は例外伝播します（トランザクションはロールバック）。

- DuckDB 互換性
  - DuckDB の executemany に空リストを渡せない既知の問題に配慮した実装（空チェックあり）。
  - DuckDB から返る日付型に対応するユーティリティを実装。

- テストのしやすさ
  - OpenAI 呼び出し部はモジュール内でラップしており、unittest.mock.patch により置き換え可能。これにより外部 API 呼び出しをモックしてユニットテストが可能です。

- 外部依存
  - 実装は標準ライブラリ・duckdb・openai を想定。研究モジュールは pandas 等に依存せず実装されています。

### 既知の制限 / 今後の改善候補
- ai モジュールの出力検証は実装済みだが、LLM の応答スタイル変化によりパースロジックの保守が必要になる可能性あり。
- raw_financials からの指標は現時点で PER/ROE のみ。PBR や配当利回りなどは未実装。
- ETL の品質チェック（quality モジュール）は設計に含まれているが、詳細なルールや自動アクションは上位で決定する想定。

---

これまでの実装はプロジェクトの基盤機能（データ収集・前処理・ファクター計算・研究支援・AI ベースのニュース評価・市場レジーム判定）をカバーしています。今後のリリースでは運用（実行・発注）周りや UI / モニタリングの強化、さらにファクター群の拡充・研究機能の追加を予定しています。