# Changelog

すべての notable な変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」規約に準拠しています。

全般:
- 日付や現在時刻を直接参照せずに処理する（ルックアヘッドバイアス防止）。
- DuckDB を主要なローカルデータストアとして利用する設計。
- OpenAI（gpt-4o-mini）を JSON モードで呼び出し、レスポンスを厳密に検証する方針。
- API 呼び出しでの一時エラーに対して指数バックオフ＋リトライを実装し、最終的にはフェイルセーフ（例: スコア 0.0、処理スキップ）で継続する。

## [Unreleased]

- 今後のリリース向けに未確定の改善点をここに記載します。

## [0.1.0] - 2026-04-03

### Added
- 初版リリース。以下の主要コンポーネントを実装。
  - パッケージのエントリポイント（kabusys.__version__ = 0.1.0）。
  - 環境設定管理（kabusys.config）
    - .env/.env.local 自動ロード機能（プロジェクトルートの検出は .git または pyproject.toml を基準）。
    - .env の柔軟なパース（export 形式、シングル/ダブルクォート、インラインコメント処理、エスケープ対応）。
    - 自動ロード無効化のための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数取得用 _require() と Settings クラス（各種 API トークン、パス、監視閾値、環境/ログレベル検証など）。
  - AI モジュール（kabusys.ai）
    - ニュース NLP（kabusys.ai.news_nlp）
      - raw_news と news_symbols から銘柄別に記事を集約して OpenAI に一括送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む。
      - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST、UTC に変換）を実装（calc_news_window）。
      - チャンク単位（デフォルト 20 銘柄）でのバッチ処理、1 銘柄あたり記事数・文字数上限を設けることでトークン肥大化に対処。
      - JSON レスポンスのバリデーション、スコアの ±1.0 クリップ、エラー時は部分的にスキップして継続するフェイルセーフ設計。
      - DuckDB 0.10 の制約に配慮した実装（executemany に空リストを渡さない等）。
    - 市場レジーム判定（kabusys.ai.regime_detector）
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime に書き込む。
      - マクロニュース抽出（複数のキーワードで ILIKE 検索）→ LLM 呼び出し → スコア合成 → 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
      - API キー未設定時は例外を送出、API エラー時は macro_sentiment = 0.0 として処理を続行する。
  - データモジュール（kabusys.data）
    - カレンダー管理（kabusys.data.calendar_management）
      - market_calendar を用いた営業日判定/is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day の実装。
      - DB にデータがない場合は曜日ベース（土日非営業日）でフォールバック。
      - JPX カレンダーを J-Quants から差分取得して更新する夜間バッチ（calendar_update_job）を実装（バックフィル／健全性チェック付き）。
    - ETL パイプライン（kabusys.data.pipeline）
      - 差分取得 → 保存（jquants_client の save_* を利用して冪等保存）→ 品質チェック（quality モジュール）という ETL フローの基礎実装。
      - ETLResult データクラス（実行結果・品質問題・エラー一覧保持）を実装し、to_dict() による監査ログ出力をサポート。
    - ETLResult を再エクスポートする簡易インターフェース（kabusys.data.etl）。
  - 研究用モジュール（kabusys.research）
    - ファクター計算（kabusys.research.factor_research）
      - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）の計算関数を実装。
      - DuckDB 内 SQL を多用して高速・一貫性のある計算を実現。データ不足時の None ハンドリング。
    - 特徴量探索（kabusys.research.feature_exploration）
      - 将来リターン計算（calc_forward_returns）、IC（情報係数）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
      - pandas 等の外部依存を避け、標準ライブラリ＆DuckDB で完結する実装。
  - パッケージ API エクスポート
    - kabusys.__all__ に data, strategy, execution, monitoring を含める（strategy 等は将来的な拡張を想定）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- 環境変数取り扱いで OS 環境変数を保護する仕組み（.env の上書き制御と protected セット）を導入。
- OpenAI API 呼び出しは API キーを引数で注入可能にしてテスト容易性を確保（env 依存を低減）。

### Notes / Migration
- 必要な環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用、必須）
  - KABU_API_PASSWORD（kabuステーション API 用、必須）
  - OPENAI_API_KEY（AI 関連機能を利用する場合に必須。score_news / score_regime の呼び出し時に api_key を渡すことも可能）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DuckDB に期待するテーブル（主なもの）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar
  - 各関数はこれらのテーブルに依存するため、スキーマ準備が必要。
- DuckDB バージョンに依存する動作（executemany の空リスト問題等）に注意。実装は互換性を考慮しているが、古い/将来のバージョンでの動作確認を推奨。
- .env の自動ロードはプロジェクトルート検出（.git または pyproject.toml）に依存。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑制可能。
- AI モジュールは LLM レスポンスの形式に依存しているため、OpenAI 側の仕様変更に対してフォールバック（0.0 のスコアや処理スキップ）を実装しているが、API 仕様変更時は追加対応が必要な場合があります。

### Breaking Changes
- （初版のためなし）

---

問い合わせ・バグ報告や提案があれば issue を作成してください。