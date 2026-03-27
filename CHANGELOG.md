# Changelog

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
このファイルはコードベースから推測した初期リリースの変更履歴です。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（当該リリースでは該当なし）
- Fixed: 修正（当該リリースでは該当なし）
- Security: セキュリティや機密情報扱いに関する注意点

[Unreleased]
- 今後のリリースのための記録領域。

[0.1.0] - 2026-03-27
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py: バージョン定義 (__version__ = "0.1.0") と主要サブパッケージのエクスポート設定（data, strategy, execution, monitoring）。
- 設定 / 環境変数管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数からの設定自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env/.env.local 読み込み順序を実装（OS環境変数 > .env.local > .env）。.env.local は override=True のため既存変数を上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供（テスト用途）。
    - 複雑な .env 行のパース対応（export プレフィックス、シングル・ダブルクォート、バックスラッシュエスケープ、インラインコメントルール）。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境モード等のプロパティ経由で設定を取得。未設定の必須値は ValueError を送出。
    - 環境変数の妥当性チェック（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）。
- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を計算。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
    - バッチサイズ、記事数上限、1銘柄当たりの文字数トリム等のトークン肥大化対策を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンスの厳密バリデーション実装（JSON 抽出、results キー、code と score、既知コードのみ採用、数値チェック、スコアクリップ）。
    - テーブル書き込みは部分失敗耐性を持たせる（対象コードのみ DELETE → INSERT、トランザクションと ROLLBACK 保護）。
    - テスト容易性のため、OpenAI 呼び出し部分をモック差替え可能（_call_openai_api を patch）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組合せて市場レジーム（bull/neutral/bear）を日次判定し market_regime テーブルへ保存。
    - prices_daily（ルックアヘッド防止のため target_date 未満のデータのみ使用）から MA 乖離を計算。
    - raw_news からマクロキーワードでフィルタしたタイトルを抽出し、OpenAI によりマクロセンチメントをスコア化。
    - OpenAI API 呼び出しのリトライ・エラーハンドリング（RateLimit・接続・タイムアウト・5xx 等）。API 失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - 計算結果はトランザクションで冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - テスト差替え用フック（_call_openai_api）あり。
- データ処理 / ETL / カレンダー
  - src/kabusys/data/pipeline.py / etl.py
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー集約など）。
    - 差分更新・バックフィル方針・品質チェックの設計を反映（_DEFAULT_BACKFILL_DAYS 等）。
    - DuckDB を用いた最大日付検出等のユーティリティ実装。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - calendar_update_job を実装（J-Quants API から差分取得 → 保存、バックフィル、健全性チェック、例外処理）。
    - DB 登録値を優先しつつ、未登録日は曜日フォールバックで扱う設計（DB がまばらでも一貫した挙動）。
- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value 等の定量ファクター計算を実装（prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率（データ不足時は None）。
    - calc_value: 最新財務データ（target_date 以前）と株価から PER / ROE を計算（EPS が 0 または欠損時は None）。
    - DuckDB SQL を活用して効率よくウィンドウ計算を実施。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - スピアマン（ランク相関）による IC を実装し、データ不足（有効件数 < 3）時は None を返す。
    - pandas 等に依存しない純 Python 実装。
- データユーティリティ
  - src/kabusys/data/__init__.py: データサブパッケージの存在。
  - src/kabusys/data/etl.py: pipeline.ETLResult の再エクスポート。
- テスト設計配慮
  - OpenAI 呼び出しをモジュール内 private 関数で実装し、unittest.mock.patch による差替えを想定（news_nlp._call_openai_api, regime_detector._call_openai_api）。
  - DuckDB executemany に対する互換性（空パラメータ回避）対応。

Security
- 環境変数 / シークレットの扱い:
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給。未設定時は ValueError を送出して処理を中断。
  - .env 自動ロード時、既存 OS 環境変数は保護される（読み込み時の protected セット）。.env.local は override=True で上書き可能。
  - .env 読み込みでファイルアクセス失敗時は警告ログを出力し続行。機密情報の取り扱いはユーザー側が .env の管理ルールを守ること。

Notes / Limitations
- このリリースでは strategy / execution / monitoring 実装ファイルは含まれていない（パッケージ __all__ でのエクスポートはあるが、提供される実体は別途実装が必要）。
- 一部計算はデータ不足時に None を返す設計（上位でのフィルタリングを想定）。
- OpenAI 呼び出しや外部 API の失敗はフェイルセーフ（スコア 0.0 やスキップ）で設計されているため、外部障害時でもプロセス全体が停止しないが、結果の完全性は保証されない。
- DuckDB のバージョン差異（リスト型バインド等）を考慮した実装がされている（executemany の空リスト回避等）。

将来のリリースで想定する改善点（例）
- strategy / execution / monitoring の実装追加とそれらの統合テスト
- より詳細な品質チェックルールと自動アラート
- モデルのバージョニングや LLM プロンプト改善ワークフロー
- 並列化・パフォーマンスチューニング（大規模銘柄数に対するバッチ処理最適化）

---
この CHANGELOG はコードベースの現状から推測して作成しています。実際の変更履歴（コミットログ・リリースノート）が存在する場合は、それに基づいて更新してください。