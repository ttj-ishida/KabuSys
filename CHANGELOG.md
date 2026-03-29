# CHANGELOG

すべての変更は「Keep a Changelog」仕様に従って記載しています。  
バージョン付けは Semantic Versioning を想定します。

## [Unreleased]

## [0.1.0] - 2026-03-29

### Added
- パッケージの初期リリース: kabusys (日本株自動売買システム) の基本モジュール群を実装。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" と公開サブモジュール指定(__all__)を追加。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に検索して自動ロードを行い、配布後の動作を考慮。
  - .env パーサーで以下をサポート:
    - 空行・コメント、`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ。
    - クォート無し値のインラインコメント（直前がスペース/タブの場合のみ）処理。
  - .env の読み込み順序: OS 環境 > .env.local（上書き） > .env（未設定時にセット）。
  - OS 環境変数を保護する protected キーセットを導入。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - Settings クラスでアプリケーション設定を提供（J-Quants, kabuAPI, Slack, DB パス, 環境/ログレベルの検証など）。
  - 必須環境変数未設定時は明示的な ValueError を送出。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - 指定日の「前日15:00 JST ～ 当日08:30 JST」ウィンドウを JST→UTC で計算する window 関数を実装。
    - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI (gpt-4o-mini) に JSON モードでバッチ送信してセンチメントスコアを取得。
    - バッチサイズ、文字数・記事数上限、スコアクリップ、リトライ(backoff) の実装。
    - レスポンスの堅牢なバリデーションと JSON パースの補助処理（余分な前後テキストから最外側の {} を抽出）。
    - DuckDB への書き込みは部分失敗を防ぐ方針で、対象コードのみ DELETE → INSERT を行いトランザクションで保護。
    - テスト容易性のため OpenAI 呼び出し箇所はパッチ可能に実装。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム判定（bull/neutral/bear）を行う機能を実装。
    - マクロニュース抽出用のキーワードリストを定義（日本・米国・グローバル関連）。
    - OpenAI 呼び出し時のリトライ、ステータスコード判定、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - DuckDB への書き込みは冪等化（BEGIN / DELETE / INSERT / COMMIT）し、失敗時は ROLLBACK と適切なログを出力。

- データモジュール (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定ユーティリティを実装。
    - market_calendar テーブルが未取得の場合は曜日ベースでフォールバック（週末は非営業日）。
    - カレンダーがまばらでも DB 登録値を優先し、未登録日は一貫した曜日フォールバックで補完。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラーリストを保持）。
    - 差分更新、バックフィル、品質チェック収集の方針に沿った実装骨子を提供。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティを実装。
    - エクスポート用に ETLResult を再エクスポート（data.etl）。

- 研究/バックテスト向けモジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials を参照して PER / ROE を計算（最新の報告日で取得）。
    - 全関数は DuckDB SQL を用い、look-ahead バイアスに配慮した実装。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（日数）先の将来リターンを一括 SQL で取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算を実装（None／データ不足ハンドリング含む）。
    - rank / factor_summary: ランク付け・統計サマリー（count/mean/std/min/max/median）を純粋 Python で実装。
  - research パッケージの公開 API を整備（必要関数を __all__ で公開）。

- テスト性・運用上の配慮
  - OpenAI 呼び出しやファイル読み取りにパッチ/モック可能な実装（ユニットテストを想定）。
  - DuckDB の executemany が空リストを受け取れない制約に対応するため、空チェックを導入。
  - 全体的に「ルックアヘッドバイアス防止」を設計方針として明記・徹底。

### Changed
- 初版につき該当なし。

### Fixed
- 初版につき該当なし。ただし以下の堅牢化点を実装:
  - OpenAI レスポンスの JSON パースが失敗するケースに対し、前後の余計なテキストから最外側の JSON を抽出して復元する処理を追加。
  - API 失敗時は例外を投げずにフェイルセーフ値（0.0 等）で継続する処理を多くの箇所で採用（運用安定性向上）。

### Deprecated
- 初版につき該当なし。

### Removed
- 初版につき該当なし。

### Security
- 環境変数読み込み時に OS 側の既存環境変数を保護する仕組みを実装（.env による上書きを制御）。

---

補足:
- 本 CHANGELOG はコードベースから推測して作成した初期リリースの変更点一覧です。各機能の詳細動作・外部依存（OpenAI, J-Quants, kabu API 等）は実行環境での設定とデータに依存します。