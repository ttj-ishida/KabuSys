# Changelog

すべての変更は Keep a Changelog の形式に従い、重要なリリースのみを記録します。  
このファイルはコードベースから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォーム「KabuSys」の基盤機能を提供します。
主な追加点と設計上の注意点を記載します。

### Added
- パッケージ骨格
  - パッケージエントリポイントを定義（kabusys/__init__.py）。
  - 公開サブパッケージ: data, strategy, execution, monitoring を想定。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーの拡張:
    - export KEY=val 形式に対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応
    - コメント（#）の扱いに関する細かなルール
  - 環境取得ヘルパー Settings を公開（J-Quants / kabu API / Slack / DB パス / ログ設定等）
  - 必須値の取得で未設定時は ValueError を発生
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値の列挙）

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いた銘柄単位のニュース集約
    - JST ベースのニュースウィンドウ計算（前日15:00〜当日08:30 JST 対応）
    - OpenAI（gpt-4o-mini）に対するバッチ送信（最大 20 銘柄/チャンク）
    - JSON Mode を用いた応答想定と厳密なバリデーション（results リスト、code/score 等）
    - トークン肥大化対策（記事数上限・文字数トリム）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ再試行
    - レスポンスパース失敗や API エラーはフェイルセーフでスキップし、全体処理を継続
    - 成果は ai_scores テーブルに冪等的に書き込み（DELETE → INSERT）、部分失敗時に既存スコアを保護
    - テスト容易性のため OpenAI 呼び出し箇所に差し替えポイント（_call_openai_api）を用意
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
    - マクロニュースはキーワードベースで抽出（複数の日本/米国キーワード定義）
    - OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得、API失敗時は 0.0 にフォールバック
    - レジームスコアをクリップしてラベル付与（bull / neutral / bear）
    - 書き込みは market_regime テーブルへ冪等実行（BEGIN / DELETE / INSERT / COMMIT）
    - ルックアヘッドバイアス回避設計（datetime.today() を参照しない、DB クエリで排他条件を適用）

- データ基盤（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar テーブルがない場合は曜日ベース（土日除外）でフォールバック
    - next/prev などは DB 登録値を優先し、未登録日は曜日フォールバックで一貫した結果を返す
    - カレンダー夜間更新ジョブ（calendar_update_job）を実装し J-Quants API から差分取得、バックフィルと健全性チェックを実施
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー一覧を含む）
    - 差分取得、バックフィル、品質チェックの方針を採用
    - DuckDB をデータ格納/集計に使用するユーティリティ関数を実装（テーブル存在確認、最大日付取得等）
    - jquants_client 経由での取得/保存を想定

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M）、200日 MA 乖離、ATR（20日）、20日平均売買代金、出来高比率等を計算
    - raw_financials から PER / ROE を取得するバリューファクター実装
    - DuckDB 内 SQL とウィンドウ関数を活用した実装
    - データ不足時は None を返す（安全設計）
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンに対応、引数検証（1〜252 日）
    - IC（Information Coefficient）計算: スピアマンランク相関の実装（ties の平均ランク処理）
    - rank ユーティリティ、factor_summary（count/mean/std/min/max/median）を提供
    - pandas 等に依存しない純標準ライブラリ実装

### Changed
- （初回リリースにつき変更履歴はありません）

### Fixed
- （初回リリースにつき修正履歴はありません）

### Security
- 秘密情報（OpenAI API キー等）は環境変数で管理。Settings に必須チェックを実装し、未設定時に明示的な例外を発生させる設計。

### Notes / Design decisions / Known behaviors
- ルックアヘッドバイアス回避: 日付依存の関数は date/target_date 引数を受け取り、内部で datetime.today() を参照しない設計。
- OpenAI 連携: JSON Mode を利用し厳密な JSON を期待するが、パース失敗時に備えた復元処理も実装。
- フォールバック: AI API の失敗やデータ不足時はフェイルセーフにより処理を継続（0.0 や None を使用）。
- DuckDB によるバルク操作の制約（executemany に空リスト不可）を考慮した実装。
- テスト容易性: OpenAI 呼び出し箇所にモック差し替えポイントがあるためユニットテストでの外部依存排除が容易。
- 部分失敗時のデータ保護: ai_scores や market_regime への書き込みは「対象コードのみ上書き」することで、部分失敗が他データを消さないよう設計。

### Known limitations / TODO
- 一部ファイル（例: data.pipeline 内の _adjust_to_trading_day の続きなど）はソースの抜粋の関係で途中までしか確認できないため、完全実装の細部は差分がある可能性があります（実際のファイル全体で追加/修正がある場合は該当箇所を参照してください）。
- 現時点で PBR・配当利回り等のバリューメトリクスは未実装（calc_value で言及）。
- strategy / execution / monitoring サブパッケージの具体的実装は本スナップショットでは確認できないため、実装状況に応じて追って記載が必要です。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合は、それに基づいて更新してください。