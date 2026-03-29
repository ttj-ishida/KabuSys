# Changelog

すべての変更は Keep a Changelog の仕様に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

なお、ログの内容はソースコードから推測して記載しています（実装意図・設計方針に基づく要約）。

## [Unreleased]

（現時点の開発中の変更はここに記載します）

## [0.1.0] - 2026-03-29

初回公開リリース。

### Added
- パッケージ構成
  - kabusys パッケージを公開（__version__ = 0.1.0）。主要サブパッケージ: data, research, ai, monitoring（__all__ に準備）。
- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを追加。
    - プロジェクトルートは __file__ を起点に上位ディレクトリを探索し、.git または pyproject.toml を基準に特定。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パース機能の強化:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理に対応。
    - インラインコメント処理（クォートなしは直前がスペース/タブの '#' をコメントと認識）。
    - 読み込み失敗時は warnings.warn を発行して継続。
  - 環境変数取得ユーティリティ Settings を追加（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル等）。
    - 必須変数取得時に未設定なら ValueError を送出する _require を提供。
    - KABUSYS_ENV の検証、LOG_LEVEL の検証、is_live / is_paper / is_dev の便宜プロパティを実装。
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news, news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - 時間ウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime を利用）。
    - バッチ処理: 1 回の API 呼び出しで最大 20 銘柄（_BATCH_SIZE）、1 銘柄あたり最大 10 記事・3000 文字でトリム。
    - JSON Mode を利用した厳密な JSON 出力を期待し、レスポンスをバリデーションして score を ±1.0 にクリップ。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。その他の失敗はスキップして継続（フェイルセーフ）。
    - DuckDB の executemany の仕様に配慮し、空パラメータを渡さないガードを実装。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数（OpenAI API キー未指定時は例外）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の market_regime を算出。
    - マクロニュースは news_nlp の calc_news_window を利用してウィンドウを決定し、raw_news からマクロキーワードに一致するタイトルを抽出。
    - OpenAI（gpt-4o-mini）へ JSON 出力を要求し、レスポンスパースや API エラーはフェイルセーフで macro_sentiment=0.0 にフォールバック。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）で market_regime テーブルに保存する。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）。
- Research（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（PBR・配当利回りは未実装）。
    - 全関数は prices_daily / raw_financials のみ参照し、外部 API へはアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）を計算。有効レコードが 3 件未満なら None を返す。
    - rank: 同順位は平均ランクとするランク付け実装（丸めによる ties を考慮）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
- Data（kabusys.data）
  - calendar_management:
    - market_calendar を使った営業日判定および次/前営業日算出、期間内営業日リスト取得を実装。
    - DB にデータがあれば DB 値を優先、未登録日は曜日ベース（平日を営業日）でフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants クライアント経由で差分取得→保存（バックフィルや健全性チェックを含む）。
  - pipeline / ETL:
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - ETL パイプライン用ユーティリティ（差分取得、保存、品質チェック連携）の骨格を実装。
    - _get_max_date 等の DB ヘルパーを実装し、既存データ有無の判定やスキャン範囲制御を行う。
- 依存・設計上の注意点（ドキュメントとして実装内に明記）
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() を多くのスコア計算内部で直接参照しない設計（target_date を明示）。
  - OpenAI 呼び出しはモジュールごとに private な _call_openai_api を提供し、テスト時は patch して差し替えやすくしている。
  - DuckDB を主要なオンディスクデータストアとして利用（SQL を直接発行する実装）。
  - ログ出力による診断（logger.warning / logger.info / logger.debug を適切に使用）。

### Changed
- （初版のため特になし）

### Fixed
- （初版のため特になし）

### Security
- OpenAI API キーは引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を使用。未設定時は明示的に ValueError を出すことで漏洩・誤動作を防止。

### Deprecated
- （初版のため特になし）

### Breaking Changes
- 初版リリースのため既存互換性の議論は不要。ただし次点のバージョンで Settings や DB スキーマ変更が入る可能性あり。

### Known issues / 注意事項
- OpenAI 呼び出しは外部 API 依存のため、API 仕様・モデル名（gpt-4o-mini）や SDK の変更により動作が影響を受ける可能性がある。コード中で APIError.status_code の有無を安全に扱う処理を含め互換性に配慮している。
- DuckDB executemany の挙動（空リスト不可）に対するガードを実装しているが、運用 DB バージョン差異に注意。
- news_nlp の JSON パースでは稀に不要テキストが混入するケースを想定して最外の {..} を抽出するフォールバックを実装しているが、LLM の出力フォーマットに依存するため完全保証はない。
- calendar_update_job の動作は jquants_client（外部モジュール）に依存する。実行環境での API 資格情報やネットワーク状態を事前に確認すること。

### 環境変数（主な必須項目）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- OPENAI_API_KEY（AI 機能利用時、関数引数でも代替可能）
- KABUSYS_ENV（任意、development|paper_trading|live のいずれか。デフォルト: development）
- LOG_LEVEL（任意、DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）

---

貢献・バグ報告・改善提案は issue/PR を歓迎します。