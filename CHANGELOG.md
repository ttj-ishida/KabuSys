# CHANGELOG

このプロジェクトは Keep a Changelog の形式に従って管理します。  
リリースはセマンティックバージョニングに従います。  

未記載の変更点や補足が必要であればお知らせください。

## [0.1.0] - 2026-03-29

概要: 初期公開リリース。日本株自動売買プラットフォーム「KabuSys」の基盤機能を実装しました。以下はコードベースから推測される主要な追加機能・設計上の注意点です。

### Added
- パッケージの基本構成
  - `kabusys` パッケージ（__version__ = 0.1.0）とサブモジュールの公開 API (`data`, `strategy`, `execution`, `monitoring`) を定義。

- 環境・設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - .env の堅牢なパース実装（コメント、クォート、export プレフィックス、エスケープなどに対応）。
  - 自動読み込みの無効化オプション `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `Settings` クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / システム設定など主要設定をプロパティ経由で取得（必須変数は未設定時に ValueError を送出）。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI 関連機能 (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで一括評価。
    - バッチサイズや記事数・文字数上限、リトライ（429/ネットワーク/5xx）・指数バックオフ、レスポンス検証、スコアのクリッピング（±1.0）を実装。
    - DuckDB への冪等書き込み（DELETE → INSERT）により部分失敗時も既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可能）。
    - タイムウィンドウは JST ベースで厳密に定義（前日15:00〜当日08:30 JST の記事を対象）。ルックアヘッドバイアスを避ける設計。

  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出。
    - マクロニュースは `news_nlp.calc_news_window` で決定されるウィンドウのタイトルを抽出して評価。
    - OpenAI 呼び出しに対してリトライ・フォールバック（失敗時は macro_sentiment=0.0）や JSON パースの耐性を持つ。
    - DuckDB へ冪等的に書き込むトランザクション処理（BEGIN/DELETE/INSERT/COMMIT、失敗時 ROLLBACK）。

- データプラットフォーム関連 (`kabusys.data`)
  - カレンダー管理 (`calendar_management`)
    - JPX カレンダーの夜間更新ジョブ `calendar_update_job`、market_calendar を参照した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日）を一貫して採用。
    - 最大探索日数やバックフィル、健全性チェックなどの安全策を実装。

  - ETL / パイプライン (`pipeline`, `etl`)
    - ETL の実行結果を表す `ETLResult` データクラスを提供（取得数／保存数／品質問題／エラー等を集約）。
    - 差分更新、バックフィル、品質チェック、id_token 注入などの設計方針を反映（実装は pipeline モジュールに準拠）。
    - `data.etl` で `ETLResult` を再エクスポート。

- リサーチ機能 (`kabusys.research`)
  - ファクター計算 (`research.factor_research`)
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER/ROE）、Volatility（20日 ATR）および流動性指標を DuckDB ベースで計算する関数（calc_momentum, calc_value, calc_volatility）。
    - データ不足時の扱い（None）を明示。
  - 特徴量探索・統計 (`research.feature_exploration`)
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリ／DuckDB で完結する実装。

### Changed
- （初版のため変更履歴なし）

### Fixed
- （初版のため修正履歴なし）

### Security
- OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` で供給する設計。環境変数が未設定の場合は明示的に ValueError を送出して安全に fail-fast。

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス防止: ニュースや価格を扱う処理（score_news, score_regime, 各種計算関数）は内部で datetime.today()/date.today() を参照せず、必ず外部から渡された target_date に基づいて動作します。
- DuckDB 互換性: executemany に空リストを渡せないバージョンへの配慮（空チェックを行ってから executemany を呼ぶ）。
- フェイルセーフ: AI 呼び出しや外部 API の失敗は例外を上位に投げずフォールバック（スコア 0.0）やスキップで継続する方針をとる箇所が多い（運用継続性優先）。
- テスト支援: OpenAI 呼び出し箇所は内部関数をパッチ可能に実装しておりユニットテストで差し替えられるようにしている。

---

今後のリリースで期待される改善点（参考）
- strategy / execution / monitoring モジュールの具体的実装（現在はパッケージ公開のみ）。
- ai モジュールの追加検証（より細かいレスポンス検証、ログの拡充）。
- ETL の詳細ワークフロー実装と品質チェックルールの拡張。
- CI / テストカバレッジの明記およびサンプルデータ・起動手順のドキュメント化。

---
Keep a Changelog に準拠して、以後の変更はバージョン毎に Added/Changed/Fixed/Deprecated/Removed/Security を分けて記載してください。