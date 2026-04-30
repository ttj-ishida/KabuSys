# TODO: 銘柄指定バックテスト設計メモ

- ステータス: 未着手
- 目的: 銘柄指定バックテストを、既存の標準バックテスト設計を壊さずに追加するための設計整理
- 注意: 本ファイルは開発・設計検討用の暫定メモであり、現行の正式仕様書そのものではない

---

## 1. 背景と結論

### 現状認識

現行設計は、個別銘柄を直接指定してバックテストする形ではなく、以下の流れを前提としている。

- ユニバースを生成する
- ユニバース内の全銘柄をスコアリングする
- 上位銘柄を採用する
- ポートフォリオを構築してバックテストする

そのため、銘柄指定バックテストを追加する場合は、バックテスト層だけでなく、ユニバース生成、シグナル生成、ポートフォリオ構築、設定スキーマまで含めた一貫した設計変更が必要となる。

### 結論

単一銘柄だけを特例で通すのではなく、**バックテスト対象スコープを指定できる汎用設計**として拡張する。

推奨する基本方針は以下。

- 通常の標準バックテストはそのまま維持する
- 追加機能として `manual_codes` ベースの対象スコープ指定を導入する
- 単一銘柄指定は、その汎用スコープ指定の一形態として扱う
- 実運用適合性評価と調査用診断モードを明確に分離する

---

## 2. 最低限必要な設計変更

以下の5項目を追加・変更対象とする。

### 2.1 Backtest API に対象スコープを追加する

- `run_backtest()` に、銘柄指定の入口となる引数を追加する
- 単なる `codes: list[str]` ではなく、`scope` または `backtest_scope` を導入する
- 通常モードと銘柄指定モードを同一 API 上で切り替えられるようにする

想定例:

```python
def run_backtest(
    conn,
    start_date,
    end_date,
    initial_cash=10_000_000,
    slippage_rate=0.001,
    commission_rate=0.00055,
    max_position_pct=0.20,
    backtest_scope: BacktestScope | None = None,
    allocation_method: str = "risk_based",
) -> BacktestResult:
    ...
```

### 2.2 Strategy / Signal Generator に対象銘柄フィルタを追加する

- `generate_signals()` に `scope` を渡せるようにする
- 特徴量結合、AIスコア結合、シグナル生成対象を `scope` 内の銘柄に制限する
- ランキングは全市場順位ではなく、`scope` 内順位であることを明示する

想定例:

```python
def generate_signals(
    conn,
    target_date,
    scope: BacktestScope | None = None,
) -> DataFrame:
    ...
```

### 2.3 Universe に標準モードと手動指定モードを追加する

- 既存のユニバース生成は維持する
- 追加で、指定銘柄リストからユニバースを構成するモードを導入する
- ただし「通常フィルタを維持するモード」と「診断用に強制通過させるモード」は分離する

### 2.4 結果メタデータに実験条件を記録する

- バックテスト結果に、通常モードか銘柄指定モードかを残す
- 指定銘柄、除外銘柄、除外理由、最終有効ユニバース数を保存する
- 同じ銘柄指定でも、通常フィルタを通した結果か、強制通過かを判別可能にする

### 2.5 リスク管理・評価指標の解釈を分離する

- 単一銘柄または少数銘柄の結果を、通常の分散ポートフォリオ前提の評価と混同しない
- 銘柄指定バックテストは研究補助機能であり、標準バックテストの代替ではないことを明文化する

---

## 3. 推奨するスコープ設計

### 3.1 `BacktestScope` を導入する

想定例:

```python
@dataclass
class BacktestScope:
    mode: Literal["default_universe", "manual_codes"]
    codes: list[str] | None = None
    preserve_universe_filters: bool = True
```

### 3.2 各フィールドの意味

- `mode="default_universe"`
  - 既存の標準バックテスト
- `mode="manual_codes"`
  - 指定銘柄だけを対象にバックテストする
- `preserve_universe_filters=True`
  - 市場、流動性、履歴期間、データ品質など通常のユニバース条件を維持する
- `preserve_universe_filters=False`
  - 調査・診断用モードとして、通常ユニバース条件を満たさない銘柄も対象にできる

### 3.3 この設計を推奨する理由

- 単一銘柄指定と複数銘柄指定を同じ仕組みで扱える
- CLI、設定ファイル、アプリケーション API の責務が揃う
- 将来、ETF専用、セクター専用、小型株専用などの拡張と整合しやすい

---

## 4. 変更対象ごとの TODO

### 4.1 `documents/05_Backtest/BacktestFramework.md`

- `run_backtest()` の公開 API に `backtest_scope` を追加する案を追記する
- CLI に `--scope-mode`, `--codes`, `--preserve-universe-filters` を追加する案を追記する
- バックテスト結果にメタデータを含める方針を追記する
- 通常モードと銘柄指定モードの違いを明文化する

### 4.2 `documents/02_Strategy/UniverseDefinition.md`

- 標準ユニバースに加えて、手動指定ユニバースの概念を追加する
- `manual_filtered_universe` と `manual_raw_universe` の違いを明文化する
- `universe_history` に `universe_source`, `scope_id`, `filter_passed`, `filter_fail_reason` 等の監査項目を追加する案を整理する
- 指定銘柄が通常ユニバース条件を満たさない場合の扱いを定義する

### 4.3 `documents/02_Strategy/StrategyModel.md`

- `generate_signals()` が `scope` 指定を受け取れる設計に変更する
- シグナル生成対象を `scope` 内銘柄に限定できることを追記する
- `signal_rank` が `scope` 内順位であることを明文化する
- `breadth_stop` や `regime` は全市場ベースで計算し続けることを明記する

### 4.4 `documents/02_Strategy/PortfolioConstruction.md`

- `portfolio_mode=multi_asset` と `portfolio_mode=targeted_scope` の区別を追加する
- `max_positions = min(existing_limit, len(scope_codes))` の扱いを整理する
- 単一銘柄時に `sector_cap` が実質無効になる点を整理する
- `allocation_method` は既存の `risk_based` / `equal` / `score` を維持する方針を記載する

### 4.5 `documents/01_Data/config_schema.md`

- `strategy.universe_size` とは別に、`backtest` セクションを追加する案を追記する
- 想定フィールド:
  - `scope_mode`
  - `codes`
  - `preserve_universe_filters`
  - `allocation_method`
- 研究用条件と本番戦略条件を設定上で分離する方針を明文化する

### 4.6 `documents/00_Architecture/InterfaceSpec.md`

- `generate_signals()` に `scope` 引数を追加する案を反映する
- `build_portfolio()` が対象スコープ付きシグナルを受け取れることを整理する
- シグナル出力、ポートフォリオ出力、Signal Queue における追加メタデータの要否を検討する

### 4.7 `documents/06_RiskManagement/RiskManagement.md`

- 単一銘柄検証は通常の分散ポートフォリオ検証と同列比較しないことを明記する
- 1銘柄上限や最大保有数の既存ルールを、銘柄指定モードでどう解釈するか整理する
- 評価指標の読み方を標準バックテストと分ける注意書きを追加する

---

## 5. Universe モードの整理

### 5.1 `standard_universe`

- 既存の市場、流動性、データ品質フィルタを通した標準ユニバース
- 通常バックテストおよび本番運用の比較基準

### 5.2 `manual_filtered_universe`

- 指定コードを起点にユニバースを構成する
- ただし通常の市場・流動性・履歴期間・データ品質条件は維持する
- 標準戦略との比較対象にしてよい

### 5.3 `manual_raw_universe`

- 指定コードをそのまま採用する
- 通常ユニバース条件を満たさない銘柄も強制的に対象化できる
- 研究・診断用であり、実運用採否の根拠には使わない

---

## 6. シグナル生成時の注意点

### 維持すべきもの

- `final_score` の計算式
- Bear / Neutral / Bull のレジーム判定
- `breadth_stop`
- ギャップリスクフィルタ
- EXIT ロジック

### 変更が必要なもの

- 対象銘柄集合の決定方法
- ランキングの母集団
- シグナル生成結果に付与するメタデータ

### 設計上の注意

- 市場全体レジームと breadth 系指標は、銘柄指定モードでも全市場データで計算し続ける
- 指定銘柄数が1件でも `signal_rank` を残し、`scope` 内順位として解釈する
- `scope` が狭くても、ルックアヘッド防止や翌営業日寄付き約定の前提は変えない

---

## 7. ポートフォリオ構築時の注意点

### 原則

- 現行設計は分散投資前提である
- 銘柄指定バックテストではこの前提が弱まる、または失われる

### TODO

- `portfolio_mode` を導入するか検討する
- 単一銘柄モードでも `risk_based` をそのまま使う方針を確認する
- `max_positions` と `max_position_pct` の関係を再整理する
- `sector_cap` を単一銘柄モードでどう扱うか明記する
- 成績比較時に、標準ポートフォリオ検証と同列に扱わないルールを追加する

---

## 8. BacktestResult / 監査情報の追加候補

以下のメタデータを保持することを検討する。

- `scope_mode`
- `scope_codes`
- `preserve_universe_filters`
- `effective_universe_size`
- `excluded_codes`
- `excluded_reasons`
- `universe_source`

目的:

- 再現性の確保
- 実験条件の追跡
- 標準モードと調査モードの混同防止

---

## 9. ドキュメント上で明文化すべき新ルール

- 銘柄指定バックテストは研究補助機能であり、標準バックテストの代替ではない
- `manual_raw_universe` の結果は、実運用採否の根拠に使わない
- `manual_filtered_universe` のみ、標準戦略との比較対象として扱える
- `scope` 内ランキングであることを明示する
- 市場全体レジーム・breadth 系指標は全市場ベースで計算し続ける
- 上場廃止銘柄を含む履歴再現と、生存バイアス回避は維持する

---

## 10. 推奨する実装順

### 優先度高

1. `run_backtest` と CLI に `scope` / `codes` 指定を追加する
2. `generate_signals` に対象銘柄フィルタを追加する
3. バックテスト結果にスコープ情報を保存する

### 優先度中

1. `config_schema.md` に `backtest` セクションを追加する
2. `UniverseDefinition.md` に手動指定ユニバースを追加する
3. `PortfolioConstruction.md` に targeted scope 前提の注意点を追記する

### 優先度低

1. Signal Queue や監視テーブルへのスコープ情報伝搬の必要性を検討する
2. 将来の ETF / セクター / 小型株専用スコープとの共通化を整理する

---

## 11. 反映時の注意事項

- まずは設計として整理し、正式仕様書への反映は採用方針確定後に行う
- 実装を始める前に、研究用モードと本番評価モードを明確に分ける
- 設計反映時は、バックテスト、戦略、ポートフォリオ、リスク管理、設定スキーマの整合性を同時に確認する
- 実装差分が発生した場合は、どちらを正式仕様とするかを再確認する

---

## 12. 反映後の状態イメージ

設計反映後の到達イメージは以下。

- 標準バックテストは既存通り維持される
- 銘柄指定バックテストは `scope` 指定で実行できる
- 単一銘柄指定と複数銘柄指定を同一設計で扱える
- 通常フィルタ維持モードと調査用強制通過モードが分離される
- 結果にスコープ条件が残り、再現性と監査性が担保される
- 研究用検証結果と標準戦略評価結果を混同しない設計になる
